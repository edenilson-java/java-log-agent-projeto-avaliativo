"""
Tendência e risco sobre uma série de execuções de pipeline.

A série fornecida pelo projeto é **simulada** e declara `"simulated": true`.
`load_pipeline_runs` recusa qualquer envelope que não declare esse rótulo
explicitamente. Essa validação exige a declaração da natureza do dado; ela não
verifica de forma independente a procedência da série.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS_PATH = (
    PROJECT_ROOT / "examples" / "devops" / "pipeline_runs.json"
).resolve()

FASES_EXIGIDAS = ("baseline", "recent")
STATUS_FALHA = "failed"
CAMPOS_DA_EXECUCAO = ("id", "phase", "duration_seconds", "status")

# O crescimento entra saturado em 100 para que uma duração explosiva não apague
# a contribuição da taxa de falha, que pesa mais por ser sintoma consumado.
TETO_CRESCIMENTO = 100.0
PESO_CRESCIMENTO = 0.4
PESO_FALHA = 0.6
CASAS_DECIMAIS = 2


def load_pipeline_runs(runs_path: str | Path | None = None) -> list[dict]:
    """
    Carrega a série de execuções, recusando qualquer dado não rotulado.

    Levanta `ValueError` se a série não estiver marcada como simulada, se não
    houver execução alguma, se faltar uma das fases comparadas ou se alguma
    execução estiver incompleta; `TypeError` se o arquivo não trouxer o objeto
    da série.
    """
    caminho = Path(runs_path) if runs_path is not None else DEFAULT_RUNS_PATH
    dados = json.loads(caminho.read_text(encoding="utf-8"))

    if not isinstance(dados, dict):
        raise TypeError(
            "Série recusada: o arquivo não contém um objeto com os metadados "
            "da série."
        )

    if dados.get("simulated") is not True:
        raise ValueError(
            'Série recusada: falta o rótulo obrigatório "simulated": true. '
            "Dados de pipeline só entram no cálculo declarados como simulados."
        )

    runs = dados.get("runs") or []
    if not runs:
        raise ValueError(
            "Série recusada: nenhuma execução para calcular. Média de conjunto "
            "vazio não é zero, é indefinida."
        )

    for posicao, execucao in enumerate(runs):
        faltando = [c for c in CAMPOS_DA_EXECUCAO if c not in execucao]
        if faltando:
            raise ValueError(
                f"Série recusada: execução na posição {posicao} sem os campos "
                f"{', '.join(faltando)}."
            )

    fases_presentes = {execucao["phase"] for execucao in runs}
    ausentes = [fase for fase in FASES_EXIGIDAS if fase not in fases_presentes]
    if ausentes:
        raise ValueError(
            f"Série recusada: sem execução da fase {', '.join(ausentes)}. "
            "A comparação exige as duas fases."
        )

    return list(runs)


def calculate_pipeline_metrics(runs: list[dict]) -> dict[str, float]:
    """
    Calcula as cinco métricas da série, arredondadas a duas casas.

    O arredondamento é só de apresentação: a ponderação do risco usa os valores
    integrais, para que a saturação do crescimento não dependa da casa decimal.
    """
    duracoes_baseline = [
        execucao["duration_seconds"] for execucao in runs
        if execucao["phase"] == "baseline"
    ]
    duracoes_recentes = [
        execucao["duration_seconds"] for execucao in runs
        if execucao["phase"] == "recent"
    ]

    baseline_average = sum(duracoes_baseline) / len(duracoes_baseline)
    recent_average = sum(duracoes_recentes) / len(duracoes_recentes)

    if baseline_average == 0:
        raise ValueError(
            "Série recusada: baseline com duração média zero; não há base de "
            "comparação para o crescimento."
        )

    growth_percent = (recent_average - baseline_average) / baseline_average * 100
    falhas = sum(1 for execucao in runs if execucao["status"] == STATUS_FALHA)
    failure_rate_percent = falhas / len(runs) * 100

    normalized_growth = min(TETO_CRESCIMENTO, max(0.0, growth_percent))
    risk_score_percent = (
        PESO_CRESCIMENTO * normalized_growth + PESO_FALHA * failure_rate_percent
    )

    return {
        "baseline_average": round(baseline_average, CASAS_DECIMAIS),
        "recent_average": round(recent_average, CASAS_DECIMAIS),
        "growth_percent": round(growth_percent, CASAS_DECIMAIS),
        "failure_rate_percent": round(failure_rate_percent, CASAS_DECIMAIS),
        "risk_score_percent": round(risk_score_percent, CASAS_DECIMAIS),
    }


def main() -> int:
    """Imprime as métricas da série padrão em JSON com chaves ordenadas."""
    metricas = calculate_pipeline_metrics(load_pipeline_runs())
    print(json.dumps(metricas, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

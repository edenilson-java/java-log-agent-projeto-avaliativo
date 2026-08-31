import json
from pathlib import Path

import pytest
import yaml

from src.devops import (
    DEFAULT_RUNS_PATH,
    calculate_pipeline_metrics,
    load_pipeline_runs,
    main,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"

# Valores literais, nao importados de `src.devops`: um teste ancorado na
# constante que deveria guardar acompanha a mudanca em vez de recusa-la.
BASELINE_AVERAGE = 13.67
RECENT_AVERAGE = 32.5
GROWTH_PERCENT = 137.8
FAILURE_RATE_PERCENT = 40.0
RISK_SCORE_PERCENT = 64.0


def execucao(identificador, fase, duracao, status):
    return {
        "id": identificador,
        "phase": fase,
        "duration_seconds": duracao,
        "status": status,
    }


def gravar_serie(caminho, runs, simulated=True, com_rotulo=True):
    conteudo = {"purpose": "serie sintetica de teste", "runs": runs}
    if com_rotulo:
        conteudo["simulated"] = simulated
    caminho.write_text(json.dumps(conteudo), encoding="utf-8")
    return caminho


# --------------------------------------------------- os valores congelados


def test_metricas_reproduzem_os_cinco_valores_congelados():
    metricas = calculate_pipeline_metrics(load_pipeline_runs())

    assert metricas == {
        "baseline_average": BASELINE_AVERAGE,
        "recent_average": RECENT_AVERAGE,
        "growth_percent": GROWTH_PERCENT,
        "failure_rate_percent": FAILURE_RATE_PERCENT,
        "risk_score_percent": RISK_SCORE_PERCENT,
    }


def test_serie_do_projeto_tem_as_cinco_execucoes_previstas():
    runs = load_pipeline_runs()

    assert [(r["id"], r["duration_seconds"], r["status"]) for r in runs] == [
        ("baseline-1", 12, "passed"),
        ("baseline-2", 14, "passed"),
        ("baseline-3", 15, "failed"),
        ("recent-1", 30, "passed"),
        ("recent-2", 35, "failed"),
    ]


def test_risco_pondera_crescimento_saturado_e_taxa_de_falha():
    # 0,4 x 100 (crescimento saturado) + 0,6 x 40 (taxa de falha) = 64,0.
    metricas = calculate_pipeline_metrics(load_pipeline_runs())

    assert metricas["growth_percent"] > 100
    assert metricas["risk_score_percent"] == RISK_SCORE_PERCENT


# ------------------------------------------------ rotulo obrigatorio do dado


def test_serie_sem_rotulo_simulated_e_recusada(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json",
        [execucao("b-1", "baseline", 10, "passed"),
         execucao("r-1", "recent", 20, "passed")],
        com_rotulo=False,
    )

    with pytest.raises(ValueError, match="simulated"):
        load_pipeline_runs(caminho)


def test_serie_rotulada_como_nao_simulada_e_recusada(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json",
        [execucao("b-1", "baseline", 10, "passed"),
         execucao("r-1", "recent", 20, "passed")],
        simulated=False,
    )

    with pytest.raises(ValueError, match="simulated"):
        load_pipeline_runs(caminho)


def test_arquivo_do_projeto_declara_a_serie_como_simulada():
    bruto = json.loads(DEFAULT_RUNS_PATH.read_text(encoding="utf-8"))

    assert bruto["simulated"] is True
    assert "simulad" in bruto["purpose"].lower()


# ------------------------------------------------------- series incompletas


def test_serie_vazia_e_recusada(tmp_path):
    caminho = gravar_serie(tmp_path / "runs.json", [])

    with pytest.raises(ValueError, match="nenhuma execução"):
        load_pipeline_runs(caminho)


def test_serie_sem_fase_baseline_e_recusada(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json", [execucao("r-1", "recent", 20, "passed")]
    )

    with pytest.raises(ValueError, match="baseline"):
        load_pipeline_runs(caminho)


def test_serie_sem_fase_recent_e_recusada(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json", [execucao("b-1", "baseline", 10, "passed")]
    )

    with pytest.raises(ValueError, match="recent"):
        load_pipeline_runs(caminho)


def test_execucao_sem_campo_obrigatorio_e_recusada(tmp_path):
    incompleta = execucao("r-1", "recent", 20, "passed")
    del incompleta["duration_seconds"]
    caminho = gravar_serie(
        tmp_path / "runs.json",
        [execucao("b-1", "baseline", 10, "passed"), incompleta],
    )

    with pytest.raises(ValueError, match="duration_seconds"):
        load_pipeline_runs(caminho)


def test_arquivo_que_nao_e_objeto_e_recusado(tmp_path):
    caminho = tmp_path / "runs.json"
    caminho.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    with pytest.raises(TypeError, match="objeto"):
        load_pipeline_runs(caminho)


# ------------------------------------------------- fronteiras do crescimento


def test_crescimento_acima_do_teto_entra_saturado(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json",
        [execucao("b-1", "baseline", 10, "passed"),
         execucao("r-1", "recent", 100, "passed")],
    )

    metricas = calculate_pipeline_metrics(load_pipeline_runs(caminho))

    assert metricas["growth_percent"] == 900.0
    # Sem falha alguma, o risco é só o termo de crescimento: 0,4 x 100.
    assert metricas["risk_score_percent"] == 40.0


def test_crescimento_negativo_nao_reduz_o_risco_abaixo_de_zero(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json",
        [execucao("b-1", "baseline", 100, "passed"),
         execucao("r-1", "recent", 50, "passed")],
    )

    metricas = calculate_pipeline_metrics(load_pipeline_runs(caminho))

    assert metricas["growth_percent"] == -50.0
    assert metricas["risk_score_percent"] == 0.0


def test_taxa_de_falha_conta_todas_as_execucoes(tmp_path):
    caminho = gravar_serie(
        tmp_path / "runs.json",
        [execucao("b-1", "baseline", 10, "failed"),
         execucao("b-2", "baseline", 10, "passed"),
         execucao("r-1", "recent", 10, "failed"),
         execucao("r-2", "recent", 10, "passed")],
    )

    metricas = calculate_pipeline_metrics(load_pipeline_runs(caminho))

    assert metricas["failure_rate_percent"] == 50.0
    assert metricas["growth_percent"] == 0.0
    assert metricas["risk_score_percent"] == 30.0


# --------------------------------------------------------- saida da CLI


def test_main_imprime_json_ordenado_com_as_cinco_metricas(capsys):
    codigo = main()
    saida = capsys.readouterr().out

    assert codigo == 0
    metricas = json.loads(saida)
    assert list(metricas) == sorted(metricas)
    assert metricas["risk_score_percent"] == RISK_SCORE_PERCENT
    assert len(metricas) == 5


# ------------------------------------------------- contrato do workflow de CI


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_e_yaml_valido(workflow):
    assert isinstance(workflow, dict)
    assert workflow["name"] == "CI"


def test_workflow_declara_as_tres_etapas_exigidas(workflow):
    comandos = [
        passo.get("run", "").strip()
        for passo in workflow["jobs"]["qualidade"]["steps"]
    ]

    assert "ruff check src tests" in comandos
    assert "pytest -q --disable-warnings" in comandos
    assert "python -m compileall -q src" in comandos


def test_workflow_nao_publica_nada_nem_pede_segredo():
    bruto = WORKFLOW.read_text(encoding="utf-8")

    assert "secrets." not in bruto
    assert "OPENAI_API_KEY" not in bruto
    for termo in ("deploy", "publish", "release", "docker push"):
        assert termo not in bruto.lower()


def test_workflow_so_pede_leitura_do_conteudo(workflow):
    assert workflow["permissions"] == {"contents": "read"}

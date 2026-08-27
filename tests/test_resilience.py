"""Testes de resiliência do modelo: timeout, tentativa única e fallback."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src import nodes, observability, tools
from src.config import load_config
from src.graph import CAMPOS_POR_EXECUCAO, create_graph
from tests.fake_llm import FakeLLM

PRINCIPAL = "examples/logs/null-pointer-exception.log"


class LLMQueEstoura(FakeLLM):
    """Simula timeout da integração."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chamadas = 0

    def invoke(self, input_data, config=None):
        self.chamadas += 1
        raise TimeoutError("Request timed out.")


class LLMQueLevanta(FakeLLM):
    """Simula exceção arbitrária da integração."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chamadas = 0

    def invoke(self, input_data, config=None):
        self.chamadas += 1
        raise RuntimeError("Connection reset by peer")


class LLMComSaidaInvalida(FakeLLM):
    """Responde fora do schema previsto."""

    def __init__(self, **kwargs):
        super().__init__(invalid_output=True, **kwargs)
        self.chamadas = 0

    def invoke(self, input_data, config=None):
        self.chamadas += 1
        return super().invoke(input_data, config)


@pytest.fixture
def executar(tmp_path, monkeypatch):
    """Roda o fluxo real com relatório e sinais confinados ao tmp."""
    saida = tmp_path / "sinais"
    monkeypatch.setenv("OUTPUT_ROOT", str(saida))
    monkeypatch.setenv("APP_LOG_PATH", str(saida / "agent-events.jsonl"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(saida / "agent-audit.jsonl"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    isolada = load_config()

    def _executar(llm):
        with (
            patch.object(tools, "OUTPUT_DIR", (tmp_path / "relatorios").resolve()),
            patch.object(nodes, "load_config", lambda: isolada),
        ):
            return create_graph(llm=llm).invoke(
                {"file_path": PRINCIPAL, "request_source": "test"}
            )

    return _executar


# --------------------------- V067: as quatro formas de falha do modelo


def test_ausencia_de_chave_cai_no_fallback(executar, monkeypatch):
    """Sem chave, nenhum modelo é construído e o fallback assume."""
    construidos = []
    monkeypatch.setattr(
        nodes, "ChatOpenAI", lambda **kwargs: construidos.append(kwargs)
    )

    final = executar(None)

    assert construidos == []
    assert final["status"] == "success_fallback"
    assert final["diagnostic"]["diagnostic_mode"] == "fallback"
    assert final["llm_attempts"] == 1


def test_timeout_cai_no_fallback_sem_retentar(executar):
    llm = LLMQueEstoura()

    final = executar(llm)

    assert final["status"] == "success_fallback"
    assert final["diagnostic"]["diagnostic_mode"] == "fallback"
    assert llm.chamadas == 1
    assert final["llm_attempts"] == 1


def test_excecao_cai_no_fallback_sem_retentar(executar):
    llm = LLMQueLevanta()

    final = executar(llm)

    assert final["status"] == "success_fallback"
    assert final["diagnostic"]["diagnostic_mode"] == "fallback"
    assert llm.chamadas == 1
    assert final["llm_attempts"] == 1


def test_saida_invalida_cai_no_fallback_sem_retentar(executar):
    llm = LLMComSaidaInvalida()

    final = executar(llm)

    assert final["status"] == "success_fallback"
    assert final["diagnostic"]["diagnostic_mode"] == "fallback"
    assert llm.chamadas == 1
    assert final["llm_attempts"] == 1


@pytest.mark.parametrize(
    "construir",
    [LLMQueEstoura, LLMQueLevanta, LLMComSaidaInvalida],
    ids=["timeout", "excecao", "saida invalida"],
)
def test_toda_falha_produz_diagnostico_e_relatorio(executar, construir):
    """Falhar no modelo não impede o agente de concluir."""
    final = executar(construir())

    assert final["status"] == "success_fallback"
    assert final["diagnostic"]["summary"]
    assert final["diagnostic"]["recommendations"]
    assert final["report_path"]


def test_caminho_feliz_tambem_conta_a_tentativa(executar):
    """A tentativa é contada em qualquer desfecho, não só na falha."""
    final = executar(FakeLLM())

    assert final["status"] == "success"
    assert final["diagnostic"]["diagnostic_mode"] == "llm"
    assert final["llm_attempts"] == 1


def test_rota_bloqueada_nao_gasta_tentativa(tmp_path, monkeypatch):
    """Sem chamada ao modelo, o contador permanece em zero."""
    saida = tmp_path / "sinais"
    monkeypatch.setenv("OUTPUT_ROOT", str(saida))
    monkeypatch.setenv("APP_LOG_PATH", str(saida / "agent-events.jsonl"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(saida / "agent-audit.jsonl"))
    isolada = load_config()
    llm = LLMQueEstoura()

    with (
        patch.object(tools, "OUTPUT_DIR", (tmp_path / "relatorios").resolve()),
        patch.object(nodes, "load_config", lambda: isolada),
    ):
        final = create_graph(llm=llm).invoke({
            "file_path": "examples/logs/adversarial-prompt-injection.log",
            "request_source": "test",
        })

    assert final["status"] == "blocked"
    assert llm.chamadas == 0
    assert final["llm_attempts"] == 0


# ------------------------------------------- limites vindos da configuração


def test_configuracao_permite_uma_unica_tentativa():
    """O limite é do tipo, não de uma verificação em tempo de execução."""
    assert load_config().max_llm_attempts == 1


def test_timeout_e_configuravel_e_limitado():
    padrao = load_config()

    assert padrao.llm_timeout_seconds == 20.0

    ajustado = load_config(env={"LLM_TIMEOUT_SECONDS": "5"})
    assert ajustado.llm_timeout_seconds == 5.0

    for fora_do_limite in ("0", "-1", "999"):
        with pytest.raises(ValidationError):
            load_config(env={"LLM_TIMEOUT_SECONDS": fora_do_limite})


def test_modelo_construido_recebe_timeout_e_zero_retentativas(monkeypatch):
    """Sem retentativa da biblioteca: o limite de uma tentativa é do agente."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk" + "-" + ("Z" * 32))
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    configurada = load_config()

    with (
        patch.object(nodes, "load_config", lambda: configurada),
        patch.object(nodes, "ChatOpenAI") as modelo_falso,
    ):
        modelo_falso.return_value.with_structured_output.return_value.invoke.side_effect = (
            RuntimeError("sem rede")
        )
        nodes.make_diagnosticar(None)({"category": "Code", "evidence": ["x"]})

    modelo_falso.assert_called_once_with(
        model="gpt-4o-mini",
        temperature=0,
        timeout=7.0,
        max_retries=0,
    )


# ------------------ a causa do fallback chega aos dois sinais


def ler_jsonl(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    return [
        json.loads(linha)
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]


@pytest.fixture
def executar_com_sinais(tmp_path, monkeypatch):
    """Roda o fluxo real e devolve o estado com as linhas dos dois sinais."""
    saida = tmp_path / "sinais"
    monkeypatch.setenv("OUTPUT_ROOT", str(saida))
    monkeypatch.setenv("APP_LOG_PATH", str(saida / "agent-events.jsonl"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(saida / "agent-audit.jsonl"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    isolada = load_config()

    def _executar(llm, caminho=PRINCIPAL, estado_extra=None):
        with (
            patch.object(tools, "OUTPUT_DIR", (tmp_path / "relatorios").resolve()),
            patch.object(nodes, "load_config", lambda: isolada),
            patch.object(observability, "load_config", lambda: isolada),
        ):
            final = create_graph(llm=llm).invoke({
                "file_path": caminho,
                "request_source": "test",
                **(estado_extra or {}),
            })
        return (
            final,
            ler_jsonl(Path(isolada.app_log_path)),
            ler_jsonl(Path(isolada.audit_log_path)),
        )

    return _executar


FORMAS_DE_FALHA = [
    pytest.param(None, "OPENAI_API_KEY", id="ausencia de chave"),
    pytest.param(LLMQueEstoura, "Request timed out", id="timeout"),
    pytest.param(LLMQueLevanta, "Connection reset by peer", id="excecao"),
    pytest.param(LLMComSaidaInvalida, "Erro de validação Pydantic", id="saida invalida"),
]


@pytest.mark.parametrize(("construir", "marca_da_causa"), FORMAS_DE_FALHA)
def test_fallback_preserva_o_contrato_e_registra_a_causa(
    executar_com_sinais, construir, marca_da_causa
):
    """O desfecho público continua limpo e os sinais dizem por que houve
    fallback."""
    llm = None if construir is None else construir()

    final, eventos, auditoria = executar_com_sinais(llm)

    assert final["status"] == "success_fallback"
    assert final["error"] == ""
    assert final["llm_attempts"] == 1

    assert len(eventos) == 1
    assert len(auditoria) == 1
    assert auditoria[0]["decision"] == "diagnosed_by_fallback"
    assert eventos[0]["decision"] == "diagnosed_by_fallback"

    for linha in (eventos[0], auditoria[0]):
        assert linha["error"], "o sinal perdeu a causa do fallback"
        assert marca_da_causa in linha["error"]


def test_as_quatro_causas_sao_distinguiveis_entre_si(executar_com_sinais):
    """A causa registrada identifica qual das quatro formas ocorreu."""
    causas = []
    for construir, _ in [(c.values[0], c.values[1]) for c in FORMAS_DE_FALHA]:
        llm = None if construir is None else construir()
        _, _, auditoria = executar_com_sinais(llm)
        causas.append(auditoria[-1]["error"])

    assert len(set(causas)) == 4


@pytest.mark.parametrize(
    ("caminho", "status_esperado"),
    [
        (PRINCIPAL, "success"),
        ("examples/logs/application-clean.log", "success_no_errors"),
    ],
    ids=["sucesso", "log limpo"],
)
def test_sem_falha_o_campo_de_erro_dos_sinais_fica_nulo(
    executar_com_sinais, caminho, status_esperado
):
    """Controle negativo: não houve erro, então o sinal não inventa um."""
    final, eventos, auditoria = executar_com_sinais(FakeLLM(), caminho=caminho)

    assert final["status"] == status_esperado
    assert eventos[0]["error"] is None
    assert auditoria[0]["error"] is None


def test_causa_nao_vaza_para_a_execucao_seguinte_da_thread(executar_com_sinais):
    """Controle negativo: a causa é de uma execução, não da thread."""
    primeira, _, _ = executar_com_sinais(
        LLMQueEstoura(), estado_extra={"thread_id": "sessao-1"}
    )
    assert primeira["fallback_reason"]

    segunda, _, auditoria = executar_com_sinais(
        FakeLLM(), estado_extra={"thread_id": "sessao-1"}
    )

    assert segunda["status"] == "success"
    assert segunda["fallback_reason"] == ""
    assert auditoria[-1]["error"] is None


def test_causa_do_fallback_e_redigida_antes_de_ir_ao_sinal(executar_com_sinais):
    """Uma credencial na mensagem da integração não chega ao arquivo."""
    segredo = "sk" + "-" + ("Q" * 32)

    class LLMQueVazaSegredo(FakeLLM):
        def invoke(self, input_data, config=None):
            raise RuntimeError(f"auth failed for {segredo}")

    final, eventos, auditoria = executar_com_sinais(LLMQueVazaSegredo())

    assert final["status"] == "success_fallback"
    bruto = json.dumps(eventos) + json.dumps(auditoria)
    assert segredo not in bruto
    assert "Q" * 16 not in bruto
    assert "[REDACTED]" in auditoria[0]["error"]


def test_causa_registrada_tem_teto(executar_com_sinais):
    """Mensagem enorme da integração não vira uma linha de sinal enorme."""

    class LLMVerborragico(FakeLLM):
        def invoke(self, input_data, config=None):
            raise RuntimeError("detalhe " * 500)

    _, eventos, auditoria = executar_com_sinais(LLMVerborragico())

    assert len(auditoria[0]["error"]) == observability.LIMITE_CAUSA_NO_SINAL
    assert len(eventos[0]["error"]) == observability.LIMITE_CAUSA_NO_SINAL


def test_causa_padrao_quando_nao_ha_mensagem_anterior():
    """Diagnóstico ausente sem causa reportada ainda registra algo útil."""
    saida = nodes.tratar_saida_invalida({"exceptions": [], "evidence": []})

    assert saida["error"] == ""
    assert saida["fallback_reason"] == nodes.CAUSA_FALLBACK_PADRAO
    assert saida["status"] == "success_fallback"


def test_causa_anterior_do_estado_e_reaproveitada():
    """Se a etapa anterior já reportou causa, ela é preservada."""
    saida = nodes.tratar_saida_invalida({
        "error": "Falha na geração do diagnóstico com LLM: x",
        "exceptions": [],
        "evidence": [],
    })

    assert saida["error"] == ""
    assert saida["fallback_reason"] == "Falha na geração do diagnóstico com LLM: x"


def test_fallback_reason_e_zerado_a_cada_execucao():
    """O contrato da limpeza, explícito."""
    assert CAMPOS_POR_EXECUCAO["fallback_reason"] == ""

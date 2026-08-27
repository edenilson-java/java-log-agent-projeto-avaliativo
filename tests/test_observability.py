"""Testes dos dois sinais correlacionados de observabilidade.

Segredos sintéticos são construídos em runtime para não gerar falsos
alertas na varredura do próprio código de teste.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src import nodes, tools
from src.config import load_config
from src.graph import create_graph
from src.observability import (
    CAMPOS_NAO_REGISTRAVEIS,
    ESTAGIO,
    _append_jsonl,
    _scrub,
    build_events,
    decide,
    emit_signals,
)
from src.schemas import AuditEvent
from tests.fake_llm import FakeLLM

RAIZ = Path(__file__).resolve().parent.parent
LOGS = RAIZ / "examples" / "logs"
PRINCIPAL = "examples/logs/null-pointer-exception.log"
LIMPO = "examples/logs/application-clean.log"
ADVERSARIAL = "examples/logs/adversarial-prompt-injection.log"


def segredo_provedor() -> str:
    return "sk" + "-" + ("A" * 32)


def segredo_github() -> str:
    return "ghp" + "_" + ("B" * 30)


@pytest.fixture
def config_isolada(tmp_path, monkeypatch):
    """Aponta os dois sinais para o diretório temporário do teste."""
    saida = tmp_path / "sinais"
    monkeypatch.setenv("OUTPUT_ROOT", str(saida))
    monkeypatch.setenv("APP_LOG_PATH", str(saida / "agent-events.jsonl"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(saida / "agent-audit.jsonl"))
    return load_config()


def ler_jsonl(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    return [
        json.loads(linha)
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]


@pytest.fixture
def executar(config_isolada, tmp_path):
    """Roda o fluxo real com a escrita e os sinais confinados ao tmp."""

    def _executar(caminho, estado_extra=None, conteudo=None):
        llm = FakeLLM()
        with (
            patch.object(tools, "OUTPUT_DIR", (tmp_path / "relatorios").resolve()),
            patch.object(nodes, "load_config", lambda: config_isolada),
        ):
            if conteudo is not None:
                with (
                    patch.object(nodes, "validate_log_file", return_value=(True, [])),
                    patch.object(nodes, "read_log_file", return_value=(True, conteudo)),
                ):
                    return create_graph(llm=llm).invoke(
                        {"file_path": caminho, "request_source": "test", **(estado_extra or {})}
                    )
            return create_graph(llm=llm).invoke(
                {"file_path": caminho, "request_source": "test", **(estado_extra or {})}
            )

    _executar.eventos = lambda: ler_jsonl(Path(config_isolada.app_log_path))
    _executar.auditoria = lambda: ler_jsonl(Path(config_isolada.audit_log_path))
    return _executar


# ------------------------------------------------ V063: correlação


def test_os_dois_sinais_sao_gravados_com_a_mesma_correlacao(executar):
    """Uma execução, duas linhas, o mesmo par de identificadores."""
    final = executar(PRINCIPAL)

    eventos = executar.eventos()
    auditoria = executar.auditoria()

    assert len(eventos) == 1
    assert len(auditoria) == 1

    assert eventos[0]["correlation_id"] == final["correlation_id"]
    assert auditoria[0]["correlation_id"] == final["correlation_id"]
    assert eventos[0]["audit_id"] == final["audit_id"]
    assert auditoria[0]["audit_id"] == final["audit_id"]
    assert final["correlation_id"] != final["audit_id"]


def test_os_dois_sinais_trazem_decisao_status_latencia_e_erro(executar):
    executar(PRINCIPAL)

    for linha in (executar.eventos()[0], executar.auditoria()[0]):
        assert linha["stage"] == ESTAGIO
        assert linha["decision"] == "diagnosed_by_model"
        assert linha["status"] == "success"
        assert linha["latency_ms"] >= 0
        assert "error" in linha
        assert linha["timestamp"]


def test_apenas_o_log_de_aplicacao_leva_o_campo_livre(executar):
    """A auditoria carrega o subconjunto decisório, sem `details`."""
    executar(PRINCIPAL)

    assert "details" in executar.eventos()[0]
    assert "details" not in executar.auditoria()[0]


def test_cada_execucao_acrescenta_uma_linha_em_cada_sinal(executar):
    executar(PRINCIPAL)
    executar(LIMPO)

    assert len(executar.eventos()) == 2
    assert len(executar.auditoria()) == 2
    correlacoes = {linha["correlation_id"] for linha in executar.auditoria()}
    assert len(correlacoes) == 2


# ------------------------------------------------ V064: redaction


def test_nenhum_segredo_do_log_chega_aos_sinais(executar):
    """Segredo presente no arquivo analisado não aparece em nenhum sinal."""
    segredo = segredo_provedor()
    conteudo = (
        "2026-07-18 ERROR Falha de autenticação\n"
        f"java.lang.SecurityException: invalid credential {segredo}\n"
    )

    executar("x.log", conteudo=conteudo)

    bruto = json.dumps(executar.eventos()) + json.dumps(executar.auditoria())

    assert segredo not in bruto
    assert "A" * 16 not in bruto
    # Os sinais não carregam evidência nem conteúdo lido: não há onde o
    # segredo aparecer, redigido ou não.
    assert "evidence" not in bruto
    assert "log_content" not in bruto


def test_conteudo_bruto_do_log_nunca_vai_para_arquivo(executar):
    executar(PRINCIPAL)

    bruto = json.dumps(executar.eventos())

    assert "NullPointerException: Cannot invoke" not in bruto
    assert "log_content" not in json.dumps(executar.eventos()[0]["details"])


def test_scrub_e_recursivo_em_dicionario_lista_e_tupla():
    segredo = segredo_github()
    payload = {
        "nivel1": {"nivel2": [{"nivel3": ("texto com " + segredo,)}]},
        "lista": ["limpo", segredo],
    }

    saido = _scrub(payload)

    assert segredo not in json.dumps(saido)
    assert "B" * 16 not in json.dumps(saido)
    assert saido["lista"][0] == "limpo"


CHAVES_QUE_NAO_VAO_PARA_ARQUIVO = [
    "log_content",
    "openai_api_key",
    "api_key",
    "apikey",
    "password",
    "senha",
    "secret",
    "token",
    "credential",
    "credencial",
]


def test_a_lista_de_campos_nao_registraveis_e_a_prevista():
    """Os nomes ficam escritos aqui, não derivados da constante vigiada."""
    assert sorted(CAMPOS_NAO_REGISTRAVEIS) == sorted(
        CHAVES_QUE_NAO_VAO_PARA_ARQUIVO
    )


@pytest.mark.parametrize("chave", CHAVES_QUE_NAO_VAO_PARA_ARQUIVO)
def test_scrub_substitui_campo_de_nome_sensivel(chave):
    """O nome da chave basta: o valor não é inspecionado, é substituído."""
    assert _scrub({chave: "qualquer valor"})[chave] == "[REDACTED]"
    assert _scrub({chave.upper(): "qualquer valor"})[chave.upper()] == "[REDACTED]"


def test_scrub_preserva_tipos_nao_textuais():
    entrada = {"n": 1, "f": 1.5, "b": True, "nulo": None}

    assert _scrub(entrada) == entrada


# ------------------------------------------------ V065: investigação


def test_filtrar_pelos_dois_sinais_reconstroi_a_execucao(executar):
    """Um `correlation_id` cruzando os dois arquivos devolve a execução."""
    primeira = executar(PRINCIPAL)
    executar(LIMPO)
    terceira = executar(ADVERSARIAL)

    alvo = terceira["correlation_id"]
    eventos = [e for e in executar.eventos() if e["correlation_id"] == alvo]
    auditoria = [a for a in executar.auditoria() if a["correlation_id"] == alvo]

    assert len(eventos) == 1
    assert len(auditoria) == 1
    assert alvo != primeira["correlation_id"]

    assert auditoria[0]["status"] == "blocked"
    assert auditoria[0]["decision"] == "blocked_by_policy"
    assert auditoria[0]["error"]
    assert eventos[0]["details"]["requires_human"] is True
    assert sorted(eventos[0]["details"]["security_flags"]) == [
        "external_action_request",
        "prompt_injection",
        "secret_request",
    ]


# ------------------------------------------------ V066: todas as rotas


@pytest.mark.parametrize(
    ("rotulo", "entrada", "status_esperado", "decisao_esperada"),
    [
        ("sucesso", {"file_path": PRINCIPAL}, "success", "diagnosed_by_model"),
        ("log limpo", {"file_path": LIMPO}, "success_no_errors", "clean_log_no_diagnosis"),
        ("bloqueio", {"file_path": ADVERSARIAL}, "blocked", "blocked_by_policy"),
        (
            "entrada invalida",
            {"file_path": "examples/logs/inexistente.log"},
            "error",
            "rejected_invalid_input",
        ),
        (
            "cancelamento",
            {"file_path": PRINCIPAL, "cancel_requested": True},
            "cancelled",
            "cancelled_by_request",
        ),
        (
            "limite de passos",
            {"file_path": PRINCIPAL, "current_step": 32, "max_steps": 32},
            "error",
            "stopped_at_step_limit",
        ),
    ],
)
def test_toda_rota_emite_os_dois_sinais(
    executar, rotulo, entrada, status_esperado, decisao_esperada
):
    caminho = entrada.pop("file_path")
    final = executar(caminho, estado_extra=entrada)

    assert final["status"] == status_esperado

    eventos = executar.eventos()
    auditoria = executar.auditoria()
    assert len(eventos) == 1, f"rota {rotulo} não emitiu o log de aplicação"
    assert len(auditoria) == 1, f"rota {rotulo} não emitiu a auditoria"
    assert auditoria[0]["decision"] == decisao_esperada
    assert auditoria[0]["correlation_id"] == final["correlation_id"]


def test_latencia_registrada_vem_do_started_at(executar):
    final = executar(PRINCIPAL)

    registrada = executar.auditoria()[0]["latency_ms"]

    assert registrada == final["latency_ms"]
    assert registrada > 0


# ------------------------------------------------ V068: falha de escrita


def test_falha_ao_gravar_nao_derruba_o_fluxo(tmp_path, monkeypatch):
    """O destino aponta para dentro de um arquivo, de modo que a criação do
    diretório falhe de verdade."""
    obstaculo = tmp_path / "isto-e-um-arquivo"
    obstaculo.write_text("nao sou diretorio", encoding="utf-8")

    monkeypatch.setenv("OUTPUT_ROOT", str(obstaculo / "saida"))
    monkeypatch.setenv("APP_LOG_PATH", str(obstaculo / "saida" / "eventos.jsonl"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(obstaculo / "saida" / "audit.jsonl"))
    quebrada = load_config()

    with (
        patch.object(tools, "OUTPUT_DIR", (tmp_path / "relatorios").resolve()),
        patch.object(nodes, "load_config", lambda: quebrada),
    ):
        final = create_graph(llm=FakeLLM()).invoke(
            {"file_path": PRINCIPAL, "request_source": "test"}
        )

    assert final["status"] == "success"
    assert final["diagnostic"]["diagnostic_mode"] == "llm"

    erros = final["observability_errors"]
    assert len(erros) == 2
    assert any("log de aplicação" in e for e in erros)
    assert any("registro de auditoria" in e for e in erros)


def test_emit_signals_devolve_lista_vazia_quando_grava(config_isolada):
    estado = {
        "correlation_id": "c-1",
        "audit_id": "a-1",
        "status": "success",
        "latency_ms": 1.0,
    }

    assert emit_signals(estado, config_isolada) == []
    assert Path(config_isolada.app_log_path).exists()
    assert Path(config_isolada.audit_log_path).exists()


def test_emit_signals_nao_levanta_com_estado_incompleto(config_isolada):
    """Estado sem correlação vira erro registrado, nunca exceção."""
    erros = emit_signals({}, config_isolada)

    assert erros
    assert "falha ao montar os sinais" in erros[0]


def test_append_jsonl_cria_o_diretorio(tmp_path):
    destino = tmp_path / "a" / "b" / "c" / "sinal.jsonl"

    _append_jsonl(destino, {"x": 1})
    _append_jsonl(destino, {"x": 2})

    linhas = destino.read_text(encoding="utf-8").splitlines()
    assert [json.loads(linha)["x"] for linha in linhas] == [1, 2]


# ------------------------------------------------ V069: AuditEvent


def test_audit_event_aceita_evento_bem_formado():
    evento = AuditEvent(
        timestamp="2026-08-26T12:00:00+00:00",
        correlation_id="c-1",
        audit_id="a-1",
        stage=ESTAGIO,
        decision="diagnosed_by_model",
        status="success",
        latency_ms=12.5,
    )

    assert evento.error is None
    assert sorted(evento.model_dump()) == [
        "audit_id",
        "correlation_id",
        "decision",
        "error",
        "latency_ms",
        "stage",
        "status",
        "timestamp",
    ]


BASE_VALIDA = {
    "timestamp": "2026-08-26T12:00:00+00:00",
    "correlation_id": "c-1",
    "audit_id": "a-1",
    "stage": ESTAGIO,
    "decision": "diagnosed_by_model",
    "status": "success",
    "latency_ms": 12.5,
}


@pytest.mark.parametrize(
    ("rotulo", "mudanca"),
    [
        ("status fora do domínio", {"status": "inexistente"}),
        ("correlation_id vazio", {"correlation_id": ""}),
        ("audit_id vazio", {"audit_id": ""}),
        ("stage vazio", {"stage": ""}),
        ("decision vazia", {"decision": ""}),
        ("latência negativa", {"latency_ms": -1.0}),
        ("timestamp não textual", {"timestamp": 123}),
        ("campo extra", {"payload": "não deveria caber"}),
    ],
)
def test_audit_event_recusa_evento_malformado(rotulo, mudanca):
    with pytest.raises(ValidationError):
        AuditEvent(**{**BASE_VALIDA, **mudanca})


@pytest.mark.parametrize("faltando", sorted(BASE_VALIDA))
def test_audit_event_exige_todos_os_campos(faltando):
    incompleto = {k: v for k, v in BASE_VALIDA.items() if k != faltando}

    with pytest.raises(ValidationError):
        AuditEvent(**incompleto)


# ------------------------------------------------ decisão registrada


@pytest.mark.parametrize(
    ("estado", "esperada"),
    [
        ({"status": "success"}, "diagnosed_by_model"),
        ({"status": "success_fallback"}, "diagnosed_by_fallback"),
        ({"status": "success_no_errors"}, "clean_log_no_diagnosis"),
        ({"status": "error"}, "rejected_invalid_input"),
        ({"status": "cancelled"}, "cancelled_by_request"),
        ({"status": "error", "blocked_reason": "max_steps"}, "stopped_at_step_limit"),
        ({"status": "blocked", "requires_human": True}, "blocked_by_policy"),
        ({"status": "running"}, "unknown"),
    ],
)
def test_decisao_resume_o_desfecho(estado, esperada):
    assert decide(estado) == esperada


def test_build_events_devolve_os_dois_registros_correlacionados():
    evento_app, auditoria = build_events({
        "correlation_id": "c-1",
        "audit_id": "a-1",
        "status": "success",
        "latency_ms": 3.0,
        "category": "Code",
    })

    assert evento_app["correlation_id"] == auditoria.correlation_id == "c-1"
    assert evento_app["audit_id"] == auditoria.audit_id == "a-1"
    assert evento_app["details"]["category"] == "Code"

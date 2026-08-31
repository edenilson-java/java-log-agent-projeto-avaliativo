"""
Testes de integração da API local.

Exercitam a tool e o fluxo completo através da fronteira HTTP, conferindo o
contrato e o mapeamento entre desfecho do domínio e código de status.
"""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src import observability, tools
from src.api import app, get_graph
from src.config import load_config

LOG_LIMPO = "examples/logs/application-clean.log"
LOG_COM_ERRO = "examples/logs/null-pointer-exception.log"


@pytest.fixture
def client():
    """Cliente HTTP com o cache do grafo limpo entre testes."""
    get_graph.cache_clear()
    return TestClient(app)


# ------------------------------------------------------------------ /health


def test_health_devolve_contrato_minimo(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "service": "javalog-agent"}


# ----------------------------------------------------- tool via HTTP: feliz


def test_read_log_caminho_feliz(client):
    resposta = client.post(
        "/api/v1/tools/read-log", json={"file_path": LOG_COM_ERRO}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "success"
    assert corpo["size_bytes"] > 0
    assert corpo["error"] is None
    assert "NullPointerException" in corpo["content"]


def test_read_log_devolve_caminho_portatil(client):
    """Nenhuma barra invertida do Windows na saída pública."""
    resposta = client.post(
        "/api/v1/tools/read-log", json={"file_path": LOG_COM_ERRO}
    )
    assert "\\" not in resposta.json()["file_path"]


def test_report_path_e_relativo_e_nao_revela_a_maquina(client):
    """Garante que report_path seja relativo, portátil e não revele a raiz local."""
    resposta = client.post("/api/v1/analyze", json={"file_path": LOG_LIMPO})
    caminho = resposta.json()["report_path"]

    assert resposta.status_code == 200
    assert caminho == "output/report_application-clean.md"
    assert not Path(caminho).is_absolute()
    assert "\\" not in caminho
    assert not re.match(r"^[A-Za-z]:", caminho)
    assert not caminho.startswith("/")
    assert "java-log-agent-projeto-avaliativo" not in caminho


# ---------------------------------------------------- tool via HTTP: erros


def test_read_log_path_traversal_devolve_400(client):
    resposta = client.post(
        "/api/v1/tools/read-log", json={"file_path": "../../etc/passwd"}
    )

    assert resposta.status_code == 400
    corpo = resposta.json()
    assert corpo["status"] == "error"
    assert "Acesso negado" in corpo["error"]
    assert corpo["content"] == ""


def test_read_log_caminho_absoluto_externo_devolve_400(client):
    resposta = client.post(
        "/api/v1/tools/read-log", json={"file_path": "C:/Windows/win.ini"}
    )

    assert resposta.status_code == 400
    assert "Acesso negado" in resposta.json()["error"]


def test_read_log_extensao_invalida_devolve_400(client):
    resposta = client.post(
        "/api/v1/tools/read-log",
        json={"file_path": "examples/logs/inexistente.pdf"},
    )

    assert resposta.status_code == 400
    assert "Extensão inválida" in resposta.json()["error"]


def test_read_log_arquivo_inexistente_devolve_400(client):
    resposta = client.post(
        "/api/v1/tools/read-log",
        json={"file_path": "examples/logs/nao-existe.log"},
    )

    assert resposta.status_code == 400
    assert "não encontrado" in resposta.json()["error"]


# -------------------------------------------------- validação de fronteira


@pytest.mark.parametrize(
    "corpo",
    [
        {"file_path": 123},
        {"file_path": None},
        {"file_path": {"caminho": "x.log"}},
        {"file_path": ["x.log"]},
        {"file_path": ""},
        {},
        {"file_path": LOG_LIMPO, "campo_desconhecido": "x"},
    ],
)
def test_read_log_entrada_malformada_devolve_422(client, corpo):
    """Tipo errado, campo faltando ou campo desconhecido: 422, não 400."""
    resposta = client.post("/api/v1/tools/read-log", json=corpo)
    assert resposta.status_code == 422


@pytest.mark.parametrize(
    "corpo",
    [
        {"file_path": 123},
        {"file_path": LOG_LIMPO, "thread_id": 456},
        {"file_path": LOG_LIMPO, "cancel_requested": "talvez"},
        {"file_path": LOG_LIMPO, "extra": True},
        {},
    ],
)
def test_analyze_entrada_malformada_devolve_422(client, corpo):
    resposta = client.post("/api/v1/analyze", json=corpo)
    assert resposta.status_code == 422


# --------------------------------------------------- fluxo completo: 200


@patch("src.nodes.write_diagnostic_report")
def test_analyze_log_limpo_devolve_200(mock_write, client):
    mock_write.return_value = (True, "output/report_application-clean.log.md")

    resposta = client.post("/api/v1/analyze", json={"file_path": LOG_LIMPO})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "success_no_errors"
    assert corpo["diagnostic"]["diagnostic_mode"] == "deterministic"
    assert corpo["diagnostic"]["category"] == "Clean"
    assert corpo["correlation_id"]
    assert corpo["audit_id"]
    assert corpo["correlation_id"] != corpo["audit_id"]


@patch("src.nodes.write_diagnostic_report")
def test_analyze_aceita_thread_id_informado(mock_write, client):
    mock_write.return_value = (True, "output/report.md")

    resposta = client.post(
        "/api/v1/analyze",
        json={"file_path": LOG_LIMPO, "thread_id": "thread-da-api"},
    )

    assert resposta.status_code == 200


@patch("src.nodes.write_diagnostic_report")
def test_analyze_nao_expoe_conteudo_bruto_do_log(mock_write, client):
    """A resposta traz diagnóstico e correlação, nunca o log inteiro."""
    mock_write.return_value = (True, "output/report.md")

    corpo = client.post(
        "/api/v1/analyze", json={"file_path": LOG_LIMPO}
    ).json()

    assert "log_content" not in corpo
    assert "content" not in corpo


# --------------------------------------------------- fluxo completo: 400


def test_analyze_entrada_invalida_devolve_400(client):
    """Erro de domínio, não de contrato: 400."""
    resposta = client.post(
        "/api/v1/analyze", json={"file_path": "../../etc/passwd"}
    )

    assert resposta.status_code == 400
    corpo = resposta.json()
    assert corpo["status"] == "error"
    assert corpo["diagnostic"] is None
    assert "Acesso negado" in corpo["error"]


# --------------------------------------------------- fluxo completo: 409


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
def test_analyze_cancelado_devolve_409(mock_read, mock_write, client):
    """Cancelamento é recusa deliberada sobre entrada válida: 409."""
    resposta = client.post(
        "/api/v1/analyze",
        json={"file_path": LOG_LIMPO, "cancel_requested": True},
    )

    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["status"] == "cancelled"
    assert corpo["diagnostic"] is None
    mock_read.assert_not_called()
    mock_write.assert_not_called()


def test_mapa_de_status_para_http():
    """Conferência direta do mapa, complementar ao teste de endpoint."""
    from src.api import HTTP_POR_STATUS

    assert HTTP_POR_STATUS["blocked"] == 409
    assert HTTP_POR_STATUS["cancelled"] == 409
    assert HTTP_POR_STATUS["error"] == 400


def test_analyze_bloqueado_devolve_409_no_endpoint():
    """`blocked` exercitado no endpoint, não apenas no mapa.

    O grafo é substituído por um duplo que devolve um estado terminal
    bloqueado — o mesmo que o nó de segurança produzirá na E05. Assim o
    endpoint é atravessado de verdade, com o `requires_human` propagado.
    """
    from src import api

    estado_bloqueado = {
        "status": "blocked",
        "correlation_id": "corr-de-teste",
        "audit_id": "audit-de-teste",
        "error": "Ação não autorizada bloqueada; aprovação humana necessária.",
        "requires_human": True,
        # sem `diagnostic` e sem `report_path`: é o contrato do desfecho
        # bloqueado, igual ao que a fachada do grafo devolve
    }

    class GrafoBloqueado:
        def invoke(self, _estado):
            return estado_bloqueado

    api.get_graph.cache_clear()
    with patch.object(api, "get_graph", return_value=GrafoBloqueado()):
        cliente = TestClient(api.app)
        resposta = cliente.post(
            "/api/v1/analyze", json={"file_path": LOG_LIMPO}
        )

    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["status"] == "blocked"
    assert corpo["requires_human"] is True
    assert corpo["diagnostic"] is None
    assert corpo["report_path"] is None
    assert corpo["correlation_id"] == "corr-de-teste"
    assert corpo["audit_id"] == "audit-de-teste"
    assert "aprovação humana necessária" in corpo["error"]


# ------------------------------------ equivalência entre os três caminhos


def test_contrato_http_equivale_ao_da_funcao_interna(client):
    """O endpoint devolve exatamente o mesmo contrato da tool interna."""
    from src.tools import read_log_as_response

    interno = read_log_as_response(LOG_COM_ERRO).model_dump(mode="json")
    http = client.post(
        "/api/v1/tools/read-log", json={"file_path": LOG_COM_ERRO}
    ).json()

    assert http == interno


def test_contrato_http_equivale_ao_interno_tambem_no_erro(client):
    from src.tools import read_log_as_response

    interno = read_log_as_response("../../etc/passwd").model_dump(mode="json")
    http = client.post(
        "/api/v1/tools/read-log", json={"file_path": "../../etc/passwd"}
    ).json()

    assert http == interno


# ---------------------------------------------------------------------------
# Fronteira CLI (E03).
#
# A CLI é a terceira fronteira refatorada nesta etapa. Estes testes vivem
# aqui, junto com as demais fronteiras, porque a árvore entregável prevista
# no plano não contempla um `test_cli.py`. Foram acrescentados após teste de
# mutação: remover a propagação de `blocked`/`cancelled` passava despercebido
# pela suíte versionada, sendo pego só pelo script de verificação, que não é
# entregue.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status_final", "codigo_esperado"),
    [
        ("success", 0),
        ("success_fallback", 0),
        ("success_no_errors", 0),
        ("error", 1),
        ("blocked", 1),
        ("cancelled", 1),
    ],
)
def test_cli_propaga_o_desfecho_no_codigo_de_saida(
    status_final,
    codigo_esperado,
):
    """`blocked` e `cancelled` encerram com 1, como `error`."""
    import src.main as cli

    estado = {
        "status": status_final,
        "error": "mensagem" if codigo_esperado else "",
        "report_path": "output/report.md",
    }

    class GrafoFalso:
        def invoke(self, _estado):
            return estado

    with (
        patch.object(cli, "create_graph", return_value=GrafoFalso()),
        patch.object(cli.sys, "argv", ["main.py", "x.log"]),
        pytest.raises(SystemExit) as saida,
    ):
        cli.main()

    assert saida.value.code == codigo_esperado


def test_cli_preserva_o_cabecalho_literal_herdado(capsys):
    """O cabeçalho e as linhas da CLI seguem os literais do mini-projeto."""
    import src.main as cli

    class GrafoFalso:
        def invoke(self, _estado):
            return {
                "status": "success_no_errors",
                "report_path": "output/report.md",
                "diagnostic": {"diagnostic_mode": "deterministic"},
            }

    with (
        patch.object(cli, "create_graph", return_value=GrafoFalso()),
        patch.object(cli.sys, "argv", ["main.py", "meu.log"]),
        pytest.raises(SystemExit),
    ):
        cli.main()

    saida = capsys.readouterr().out
    assert "Iniciando análise do log: meu.log" in saida
    assert "Status Final: success_no_errors" in saida
    assert "Relatório gerado com sucesso em: output/report.md" in saida
    assert "Modo de diagnóstico: deterministic" in saida


# ------------------------------------------- fronteira HTTP e observabilidade


@pytest.fixture
def sinais_isolados(tmp_path, monkeypatch):
    """Confina os dois sinais e o relatório ao diretório do teste."""
    saida = tmp_path / "sinais"
    monkeypatch.setenv("OUTPUT_ROOT", str(saida))
    monkeypatch.setenv("APP_LOG_PATH", str(saida / "agent-events.jsonl"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(saida / "agent-audit.jsonl"))
    isolada = load_config()

    def ler(caminho):
        p = Path(caminho)
        if not p.exists():
            return []
        return [
            json.loads(linha)
            for linha in p.read_text(encoding="utf-8").splitlines()
            if linha.strip()
        ]

    with (
        patch.object(tools, "OUTPUT_DIR", (tmp_path / "relatorios").resolve()),
        patch.object(observability, "load_config", lambda: isolada),
    ):
        yield lambda: (
            ler(isolada.app_log_path),
            ler(isolada.audit_log_path),
        )


@pytest.mark.parametrize(
    ("caminho", "codigo_esperado"),
    [
        (LOG_LIMPO, 200),
        ("examples/logs/adversarial-prompt-injection.log", 409),
    ],
    ids=["200", "409"],
)
def test_sinal_nao_publica_status_http(
    client, sinais_isolados, caminho, codigo_esperado
):
    """O código HTTP é decidido depois da emissão; o sinal não o afirma."""
    resposta = client.post("/api/v1/analyze", json={"file_path": caminho})
    assert resposta.status_code == codigo_esperado

    eventos, auditoria = sinais_isolados()
    assert len(eventos) == 1

    assert "http_status" not in eventos[0]["details"]
    assert "http_status" not in auditoria[0]


def test_sinal_da_requisicao_correlaciona_com_a_resposta(client, sinais_isolados):
    """Os identificadores devolvidos pela API são os gravados nos sinais."""
    corpo = client.post("/api/v1/analyze", json={"file_path": LOG_LIMPO}).json()

    eventos, auditoria = sinais_isolados()

    assert eventos[0]["correlation_id"] == corpo["correlation_id"]
    assert auditoria[0]["correlation_id"] == corpo["correlation_id"]
    assert eventos[0]["audit_id"] == corpo["audit_id"]
    assert eventos[0]["details"]["request_source"] == "api"

"""
Testes de integração do servidor MCP local.

Exercitam a tool através da fronteira MCP, in-process — sem subir processo
externo e sem rede. O alvo é comprovar que o contrato é o mesmo dos outros
dois caminhos e que a capability é read-only de verdade.
"""

import asyncio
import inspect
from unittest.mock import patch

import pytest

from src.mcp_server import create_mcp_server, read_log_tool
from src.tools import read_log_as_response

LOG_COM_ERRO = "examples/logs/null-pointer-exception.log"
LOG_LIMPO = "examples/logs/application-clean.log"


def _resolver(valor):
    """Executa o retorno se for corrotina; devolve direto caso contrário."""
    if inspect.isawaitable(valor):
        return asyncio.run(valor)
    return valor


@pytest.fixture
def server():
    return create_mcp_server()


# ------------------------------------------------------- capability exposta


def test_servidor_expoe_somente_a_tool_de_leitura(server):
    """Uma única capability, e ela é read-only."""
    tools = _resolver(server.list_tools())
    nomes = [t.name for t in tools]

    assert nomes == ["read_log"]


def test_tool_declara_titulo_e_descricao(server):
    tools = _resolver(server.list_tools())
    read_log = tools[0]

    assert read_log.title == "Read Java Log"
    assert "read-only" in read_log.description or "Não executa" in read_log.description


def test_servidor_nao_expoe_recurso_nem_prompt(server):
    """Nada além da tool: sem resources e sem prompts."""
    assert _resolver(server.list_resources()) == []
    assert _resolver(server.list_prompts()) == []


# ------------------------------------------------------ contrato da tool


def test_tool_mcp_caminho_feliz():
    resultado = read_log_tool(LOG_COM_ERRO)

    assert resultado["status"] == "success"
    assert resultado["size_bytes"] > 0
    assert resultado["error"] is None
    assert "NullPointerException" in resultado["content"]


def test_tool_mcp_path_traversal_negado():
    resultado = read_log_tool("../../etc/passwd")

    assert resultado["status"] == "error"
    assert "Acesso negado" in resultado["error"]
    assert resultado["content"] == ""


def test_tool_mcp_caminho_absoluto_externo_negado():
    resultado = read_log_tool("C:/Windows/win.ini")

    assert resultado["status"] == "error"
    assert "Acesso negado" in resultado["error"]


def test_tool_mcp_extensao_invalida():
    resultado = read_log_tool("examples/logs/x.pdf")

    assert resultado["status"] == "error"
    assert "Extensão inválida" in resultado["error"]


def test_tool_mcp_entrada_vazia():
    resultado = read_log_tool("")

    assert resultado["status"] == "error"
    assert resultado["content"] == ""


def test_tool_mcp_devolve_caminho_portatil():
    resultado = read_log_tool(LOG_COM_ERRO)
    assert "\\" not in resultado["file_path"]


# ------------------------------------------- equivalência entre caminhos


def test_contrato_mcp_equivale_ao_da_funcao_interna():
    """A tool MCP devolve exatamente o contrato da função interna."""
    interno = read_log_as_response(LOG_COM_ERRO).model_dump(mode="json")
    via_mcp = read_log_tool(LOG_COM_ERRO)

    assert via_mcp == interno


def test_contrato_mcp_equivale_ao_interno_tambem_no_erro():
    interno = read_log_as_response("../../etc/passwd").model_dump(mode="json")
    via_mcp = read_log_tool("../../etc/passwd")

    assert via_mcp == interno


# ------------------------------------------------- read-only comprovado


@patch("src.tools.write_diagnostic_report")
def test_tool_mcp_nao_grava_arquivo(mock_write):
    """A capability não escreve — nem no caminho feliz, nem no de erro."""
    read_log_tool(LOG_COM_ERRO)
    read_log_tool("../../etc/passwd")

    mock_write.assert_not_called()


def test_tool_mcp_nao_chama_o_modelo():
    """Nenhum caminho da tool constrói ou invoca um modelo."""
    with patch("src.nodes.ChatOpenAI") as mock_modelo:
        read_log_tool(LOG_COM_ERRO)
        read_log_tool(LOG_LIMPO)
        read_log_tool("invalido")

    mock_modelo.assert_not_called()


def test_modulo_mcp_nao_importa_escrita_nem_modelo():
    """O módulo do servidor não tem sequer acesso às funções de escrita."""
    import src.mcp_server as servidor

    assert not hasattr(servidor, "write_diagnostic_report")
    assert not hasattr(servidor, "ChatOpenAI")
    assert not hasattr(servidor, "create_graph")


def test_conteudo_longo_e_truncado_com_marcador():
    """Resposta grande é truncada, e o truncamento é declarado."""
    from src.tools import MAX_RESPONSE_CHARS

    conteudo = "x" * (MAX_RESPONSE_CHARS + 500)
    with patch("src.tools.read_log_file", return_value=(True, conteudo)):
        resultado = read_log_tool("examples/logs/grande.log")

    assert resultado["truncated"] is True
    assert len(resultado["content"]) == MAX_RESPONSE_CHARS
    assert resultado["size_bytes"] == len(conteudo)


# ---------------------------------------------------------------------------
# Integração pela fronteira real do servidor MCP.
#
# Os testes acima chamam `read_log_tool` diretamente: isso exercita o handler,
# não o registro nem a execução pelo `MCPServer`. Os testes abaixo atravessam
# `server.call_tool(...)`, que é o caminho que um cliente MCP percorre.
# ---------------------------------------------------------------------------


def _chamar(server, nome, argumentos):
    """Executa a corrotina `call_tool` e devolve o `CallToolResult`."""
    return asyncio.run(server.call_tool(nome, argumentos))


def _estruturado(resultado):
    """Extrai o conteúdo estruturado do resultado da chamada."""
    return getattr(
        resultado,
        "structured_content",
        getattr(resultado, "structuredContent", None),
    )


def test_call_tool_caminho_feliz(server):
    """A tool é executada pelo servidor, não chamada diretamente."""
    resultado = _chamar(server, "read_log", {"file_path": LOG_COM_ERRO})

    assert resultado.is_error is False
    corpo = _estruturado(resultado)
    assert corpo["status"] == "success"
    assert corpo["size_bytes"] > 0
    assert "NullPointerException" in corpo["content"]


def test_call_tool_erro_de_dominio_vem_estruturado(server):
    """Path traversal não vira erro de protocolo: vira contrato de erro."""
    resultado = _chamar(server, "read_log", {"file_path": "../../etc/passwd"})

    assert resultado.is_error is False
    corpo = _estruturado(resultado)
    assert corpo["status"] == "error"
    assert "Acesso negado" in corpo["error"]
    assert corpo["content"] == ""


def test_call_tool_structured_content_equivale_ao_contrato_interno(server):
    """O que sai pelo servidor MCP é o contrato da função interna."""
    resultado = _chamar(server, "read_log", {"file_path": LOG_COM_ERRO})
    interno = read_log_as_response(LOG_COM_ERRO).model_dump(mode="json")

    assert _estruturado(resultado) == interno


def test_call_tool_equivalencia_tambem_no_erro(server):
    resultado = _chamar(server, "read_log", {"file_path": "../../etc/passwd"})
    interno = read_log_as_response("../../etc/passwd").model_dump(mode="json")

    assert _estruturado(resultado) == interno


def test_call_tool_recusa_tipo_errado_na_fronteira(server):
    """O SDK valida o payload antes de executar o handler."""
    from mcp.server.mcpserver.exceptions import ToolError

    with (
        patch("src.tools.read_log_file") as mock_le,
        patch("src.tools.write_diagnostic_report") as mock_escreve,
        patch("src.nodes.ChatOpenAI") as mock_modelo,
        pytest.raises(ToolError) as erro,
    ):
        _chamar(server, "read_log", {"file_path": 123})

    assert "valid string" in str(erro.value)
    mock_le.assert_not_called()
    mock_escreve.assert_not_called()
    mock_modelo.assert_not_called()


def test_call_tool_recusa_capability_inexistente(server):
    """Só existe `read_log`: qualquer outro nome é recusado pelo servidor."""
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError) as erro:
        _chamar(server, "write_report", {"filename": "x.md", "content": "y"})

    assert "Unknown tool" in str(erro.value)


def test_call_tool_nao_grava_e_nao_chama_o_modelo(server):
    """Read-only comprovado atravessando o servidor, não o handler."""
    with (
        patch("src.tools.write_diagnostic_report") as mock_escreve,
        patch("src.nodes.ChatOpenAI") as mock_modelo,
    ):
        _chamar(server, "read_log", {"file_path": LOG_COM_ERRO})
        _chamar(server, "read_log", {"file_path": LOG_LIMPO})
        _chamar(server, "read_log", {"file_path": "../../etc/passwd"})

    mock_escreve.assert_not_called()
    mock_modelo.assert_not_called()

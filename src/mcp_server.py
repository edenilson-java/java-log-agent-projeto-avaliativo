from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from src.tools import read_log_as_response


def read_log_tool(file_path: str) -> dict[str, Any]:
    """
    Lê um log permitido e devolve o contrato estruturado.

    A capability é **read-only por construção**: esta função chama apenas
    `read_log_as_response`, que envolve a leitura confinada. Não há aqui
    nenhuma chamada de escrita e nenhuma chamada ao modelo — o que o servidor
    MCP consegue fazer é exatamente o que esta função faz.
    """
    return read_log_as_response(file_path).model_dump(mode="json")


def create_mcp_server() -> MCPServer:
    """Cria o servidor MCP local expondo somente a tool de leitura."""
    server = MCPServer(
        name="javalog-agent",
        title="JavaLog Agent",
        description="Tool local e read-only para leitura segura de logs.",
        version="1.0.0",
    )
    server.tool(
        name="read_log",
        title="Read Java Log",
        description=(
            "Lê somente arquivos .log/.txt dentro de examples/logs e retorna "
            "um contrato estruturado. Não executa comandos e não grava dados."
        ),
        structured_output=True,
    )(read_log_tool)
    return server


mcp = create_mcp_server()


def main() -> None:
    """Executa o servidor pelo transporte stdio."""
    mcp.run("stdio")


if __name__ == "__main__":
    main()

from __future__ import annotations

from functools import lru_cache
from uuid import uuid4

from fastapi import FastAPI, Response, status

from src.graph import JavaLogGraph, create_graph
from src.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    DiagnosticReport,
    HealthResponse,
    ReadLogRequest,
    ReadLogResponse,
)
from src.tools import read_log_as_response

app = FastAPI(
    title="JavaLog Agent API",
    description=(
        "Backend local do agente de diagnóstico de logs Java/Spring Boot."
    ),
    version="1.0.0",
)

# Tradução entre o desfecho do domínio e o código HTTP.
#
# A distinção importa: `error` é entrada inválida do cliente (400), enquanto
# `blocked` e `cancelled` são recusas deliberadas da aplicação sobre uma
# entrada bem formada — daí 409, e não 400. O 422 não aparece aqui porque é
# produzido pelo próprio Pydantic, antes de o endpoint executar.
HTTP_POR_STATUS = {
    "error": status.HTTP_400_BAD_REQUEST,
    "blocked": status.HTTP_409_CONFLICT,
    "cancelled": status.HTTP_409_CONFLICT,
}


@lru_cache(maxsize=1)
def get_graph() -> JavaLogGraph:
    """Mantém um grafo único por processo, compartilhado entre requisições."""
    return create_graph()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Contrato mínimo de saúde, sem tocar em disco nem no modelo."""
    return HealthResponse()


@app.post("/api/v1/tools/read-log", response_model=ReadLogResponse)
def read_log(request: ReadLogRequest, response: Response) -> ReadLogResponse:
    """
    Expõe a tool read-only por HTTP.

    Devolve exatamente o mesmo contrato da função interna e da tool MCP.
    """
    resultado = read_log_as_response(request.file_path)
    if resultado.status == "error":
        response.status_code = status.HTTP_400_BAD_REQUEST
    return resultado


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze_log(request: AnalyzeRequest, response: Response) -> AnalyzeResponse:
    """Executa o fluxo completo e devolve a resposta observável."""
    thread_id = request.thread_id or str(uuid4())

    final_state = get_graph().invoke(
        {
            "file_path": request.file_path,
            "thread_id": thread_id,
            "request_source": "api",
            "cancel_requested": request.cancel_requested,
        }
    )

    status_final = final_state.get("status", "error")
    codigo = HTTP_POR_STATUS.get(status_final)
    if codigo is not None:
        response.status_code = codigo

    diagnostico_bruto = final_state.get("diagnostic")
    diagnostico = (
        DiagnosticReport(**diagnostico_bruto) if diagnostico_bruto else None
    )

    return AnalyzeResponse(
        status=status_final,
        correlation_id=final_state["correlation_id"],
        audit_id=final_state["audit_id"],
        diagnostic=diagnostico,
        report_path=final_state.get("report_path") or None,
        error=final_state.get("error") or None,
        requires_human=final_state.get("requires_human", False),
    )

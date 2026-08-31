from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from src.state import AgentStatus


class StrictModel(BaseModel):
    """
    Base para contratos de fronteira que rejeitam campos inesperados.

    `extra="forbid"` transforma payload com campo desconhecido em erro de
    validação, em vez de deixá-lo passar silenciosamente.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DiagnosticReport(StrictModel):
    """
    Modelo estruturado para o relatório de diagnóstico de logs.

    Campos, domínios e mensagens são preservados do mini-projeto; a evolução
    apenas endureceu a fronteira, herdando de `StrictModel`.
    """

    summary: str = Field(
        ...,
        min_length=1,
        description="Resumo curto e objetivo do problema encontrado.",
    )
    probable_cause: str = Field(
        ...,
        min_length=1,
        description="Causa provável do problema.",
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="Severidade do problema."
    )
    category: str = Field(
        ...,
        min_length=1,
        description=(
            "Categoria do problema (ex: Database, Network, Configuration, "
            "Code, Unknown)."
        ),
    )
    exception: str | None = Field(
        None,
        description="Nome da exceção principal identificada.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Lista de trechos de log que comprovam o problema.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Lista de ações recomendadas para resolver o problema.",
    )
    diagnostic_mode: Literal["llm", "fallback", "deterministic"] = Field(
        description="Modo de diagnóstico utilizado."
    )

    @field_validator("summary", "probable_cause", "category", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("Campo não pode estar vazio.")
        return str(v).strip()


# ---------------------------------------------------------------------------
# Contratos de fronteira (E03).
#
# Todos herdam de StrictModel: campo desconhecido vira erro de validacao, e o
# FastAPI o traduz em HTTP 422. Os tipos sao StrictStr para que numero, nulo
# ou objeto no lugar de texto tambem sejam recusados, em vez de coagidos.
# ---------------------------------------------------------------------------


class ReadLogRequest(StrictModel):
    """Entrada da tool read-only de leitura de log."""

    file_path: StrictStr = Field(min_length=1)


class ReadLogResponse(StrictModel):
    """
    Saída estruturada e limitada da tool read-only.

    É o mesmo contrato devolvido pela função interna, pelo endpoint HTTP e
    pela tool MCP — é isso que torna os três caminhos equivalentes.
    """

    status: Literal["success", "error"]
    file_path: str
    content: str = ""
    size_bytes: int = Field(default=0, ge=0)
    truncated: bool = False
    error: str | None = None


class AnalyzeRequest(StrictModel):
    """Entrada da análise exposta pela API."""

    file_path: StrictStr = Field(min_length=1)
    thread_id: StrictStr | None = Field(default=None, min_length=1)
    cancel_requested: bool = False


class AnalyzeResponse(StrictModel):
    """
    Resposta observável da análise.

    Não expõe o conteúdo bruto do log: devolve o diagnóstico estruturado e os
    identificadores que permitem correlacionar a execução nos sinais.
    """

    status: AgentStatus
    correlation_id: StrictStr = Field(min_length=1)
    audit_id: StrictStr = Field(min_length=1)
    diagnostic: DiagnosticReport | None = None
    report_path: str | None = None
    error: str | None = None
    requires_human: bool = False


class HealthResponse(StrictModel):
    """Contrato mínimo do endpoint de saúde."""

    status: Literal["ok"] = "ok"
    service: Literal["javalog-agent"] = "javalog-agent"


# Registro de auditoria: subconjunto decisório, sem payload livre.
class AuditEvent(StrictModel):
    """Linha tipada do registro de auditoria, correlacionada ao log de
    aplicação por `correlation_id` e `audit_id`."""

    timestamp: StrictStr = Field(min_length=1)
    correlation_id: StrictStr = Field(min_length=1)
    audit_id: StrictStr = Field(min_length=1)
    stage: StrictStr = Field(min_length=1)
    decision: StrictStr = Field(min_length=1)
    status: AgentStatus
    latency_ms: float = Field(ge=0)
    error: str | None = None

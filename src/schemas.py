from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

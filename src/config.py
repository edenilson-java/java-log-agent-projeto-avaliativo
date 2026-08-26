from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWED_LOG_ROOT = (PROJECT_ROOT / "examples" / "logs").resolve()
DEFAULT_OUTPUT_ROOT = (PROJECT_ROOT / "output").resolve()
DEFAULT_MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024


class AppConfig(BaseModel):
    """
    Configuração validada do JavaLog Agent, carregada sem expor segredos.

    O modelo é imutável e recusa campos desconhecidos: erro de digitação em
    variável de ambiente falha na carga, não silenciosamente em execução.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    openai_api_key: SecretStr | None = None
    openai_model: str = Field(default="gpt-4o-mini", min_length=1)
    llm_temperature: Literal[0] = 0
    llm_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    max_llm_attempts: Literal[1] = 1
    max_steps: int = Field(default=32, ge=1, le=256)
    max_log_size_bytes: int = Field(
        default=DEFAULT_MAX_LOG_SIZE_BYTES,
        ge=1,
        le=10_000_000,
    )
    allowed_log_root: Path = DEFAULT_ALLOWED_LOG_ROOT
    output_root: Path = DEFAULT_OUTPUT_ROOT
    app_log_path: Path = DEFAULT_OUTPUT_ROOT / "agent-events.jsonl"
    audit_log_path: Path = DEFAULT_OUTPUT_ROOT / "agent-audit.jsonl"

    @field_validator("openai_model", mode="before")
    @classmethod
    def validate_model_name(cls, value: object) -> str:
        """Recusa nome de modelo vazio vindo do ambiente."""
        if not value or not str(value).strip():
            raise ValueError("OPENAI_MODEL não pode estar vazio.")
        return str(value).strip()

    @field_validator(
        "allowed_log_root",
        "output_root",
        "app_log_path",
        "audit_log_path",
        mode="after",
    )
    @classmethod
    def resolve_path(cls, value: Path) -> Path:
        """Normaliza os caminhos para absolutos, sem `~` e sem componentes relativos."""
        return value.expanduser().resolve()

    @property
    def has_openai_key(self) -> bool:
        """Indica se há chave utilizável, sem revelar o valor."""
        return bool(
            self.openai_api_key
            and self.openai_api_key.get_secret_value().strip()
        )


def _value_or_default(
    source: Mapping[str, str],
    name: str,
    default: str,
) -> str:
    """Lê a variável, normaliza espaços e trata valor vazio como ausente."""
    value = source.get(name, "").strip()
    return value or default


def load_config(env: Mapping[str, str] | None = None) -> AppConfig:
    """
    Carrega a mesma configuração para CLI, API, MCP e grafo.

    O parâmetro `env` existe para os testes injetarem um ambiente sintético
    sem tocar em `os.environ`.
    """
    source = os.environ if env is None else env
    key = source.get("OPENAI_API_KEY", "").strip()
    output_root = _value_or_default(
        source,
        "OUTPUT_ROOT",
        str(DEFAULT_OUTPUT_ROOT),
    )
    output_root_path = Path(output_root).expanduser()

    return AppConfig(
        openai_api_key=SecretStr(key) if key else None,
        openai_model=_value_or_default(source, "OPENAI_MODEL", "gpt-4o-mini"),
        llm_timeout_seconds=_value_or_default(
            source,
            "LLM_TIMEOUT_SECONDS",
            "20",
        ),
        max_steps=_value_or_default(source, "MAX_STEPS", "32"),
        max_log_size_bytes=_value_or_default(
            source,
            "MAX_LOG_SIZE_BYTES",
            str(DEFAULT_MAX_LOG_SIZE_BYTES),
        ),
        allowed_log_root=_value_or_default(
            source,
            "ALLOWED_LOG_ROOT",
            str(DEFAULT_ALLOWED_LOG_ROOT),
        ),
        output_root=output_root,
        app_log_path=_value_or_default(
            source,
            "APP_LOG_PATH",
            str(output_root_path / "agent-events.jsonl"),
        ),
        audit_log_path=_value_or_default(
            source,
            "AUDIT_LOG_PATH",
            str(output_root_path / "agent-audit.jsonl"),
        ),
    )

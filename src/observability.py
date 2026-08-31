from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.config import AppConfig, load_config
from src.schemas import AuditEvent
from src.security import redact_sensitive_text, sanitize_untrusted_content
from src.state import AgentState

# Etapa a que os sinais se referem. É o ponto único de término, por onde
# passam todas as rotas, inclusive as que abortam.
ESTAGIO = "finalizar_execucao"

# Chaves cujo valor nunca vai para arquivo, independentemente do conteúdo.
CAMPOS_NAO_REGISTRAVEIS = frozenset({
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
})

# Só entram campos que a execução produziu: o código HTTP é decidido na
# fronteira, depois desta emissão.
CAMPOS_DE_DETALHE = (
    "category",
    "thread_id",
    "request_source",
    "current_step",
    "llm_attempts",
    "requires_human",
    "redacted",
    "security_flags",
    "node_history",
    "report_path",
)

# Teto da causa registrada. Mensagem de integração externa pode trazer o
# payload inteiro; uma linha de sinal não é lugar para ele.
LIMITE_CAUSA_NO_SINAL = 500

# Serializa gravações concorrentes no mesmo processo — a API mantém um grafo
# único atendendo várias requisições. Não cobre concorrência entre processos.
_TRAVA_DE_ESCRITA = threading.Lock()


def _scrub(payload: object) -> object:
    """Redige recursivamente a estrutura: chave sensível pelo nome, texto
    pela redaction."""
    if isinstance(payload, dict):
        return {
            chave: (
                "[REDACTED]"
                if str(chave).lower() in CAMPOS_NAO_REGISTRAVEIS
                else _scrub(valor)
            )
            for chave, valor in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [_scrub(item) for item in payload]
    if isinstance(payload, str):
        return redact_sensitive_text(payload)
    return payload


def _append_jsonl(caminho: Path, registro: dict[str, Any]) -> None:
    """Acrescenta uma linha JSON, criando o diretório e serializando a escrita."""
    linha = json.dumps(registro, ensure_ascii=False, sort_keys=True)
    with _TRAVA_DE_ESCRITA:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")


def decide(state: AgentState) -> str:
    """Resume em uma palavra o desfecho da execução, para os dois sinais."""
    status = state.get("status", "unknown")
    if state.get("requires_human"):
        return "blocked_by_policy"
    if status == "cancelled":
        return "cancelled_by_request"
    if state.get("blocked_reason") == "max_steps":
        return "stopped_at_step_limit"
    if status == "error":
        return "rejected_invalid_input"
    if status == "success_fallback":
        return "diagnosed_by_fallback"
    if status == "success_no_errors":
        return "clean_log_no_diagnosis"
    if status == "success":
        return "diagnosed_by_model"
    return "unknown"


def _causa_registrada(state: AgentState) -> str | None:
    """Erro final, ou a causa do fallback; `None` quando não houve erro."""
    causa = state.get("error") or state.get("fallback_reason") or ""
    if not causa:
        return None
    return sanitize_untrusted_content(causa, LIMITE_CAUSA_NO_SINAL)


def build_events(state: AgentState) -> tuple[dict[str, Any], AuditEvent]:
    """Monta os dois registros já redigidos: ambos correlacionados, apenas
    o log de aplicação com o campo livre `details`."""
    comum = {
        "timestamp": datetime.now(UTC).isoformat(),
        "correlation_id": str(state.get("correlation_id", "")),
        "audit_id": str(state.get("audit_id", "")),
        "stage": ESTAGIO,
        "decision": decide(state),
        "status": state.get("status", "error"),
        "latency_ms": float(state.get("latency_ms", 0.0) or 0.0),
        # O fallback zera o `error` público; a causa técnica continua
        # disponível e é ela que vai ao sinal, redigida e com teto.
        "error": _causa_registrada(state),
    }

    detalhes = {
        campo: state.get(campo)
        for campo in CAMPOS_DE_DETALHE
        if state.get(campo) is not None
    }
    evento_app = _scrub({**comum, "details": detalhes})

    return evento_app, AuditEvent(**_scrub(comum))


def emit_signals(
    state: AgentState,
    config: AppConfig | None = None,
) -> list[str]:
    """
    Grava os dois sinais e devolve os erros, sem levantar exceção.

    Observabilidade não derruba o fluxo que observa, e um sinal é tentado
    mesmo que o outro falhe.
    """
    cfg = config or load_config()
    erros: list[str] = []

    try:
        evento_app, evento_auditoria = build_events(state)
    except (ValidationError, TypeError, ValueError) as exc:
        return [f"falha ao montar os sinais: {type(exc).__name__}: {exc}"]

    for caminho, registro, rotulo in (
        (cfg.app_log_path, evento_app, "log de aplicação"),
        (cfg.audit_log_path, evento_auditoria.model_dump(), "registro de auditoria"),
    ):
        try:
            _append_jsonl(Path(caminho), registro)
        except OSError as exc:
            erros.append(f"falha ao gravar {rotulo}: {type(exc).__name__}: {exc}")

    return erros

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

# Os cinco primeiros status são herdados do mini-projeto e preservados por
# continuidade. Os três últimos são acrescentados pela evolução.
AgentStatus = Literal[
    "success",
    "success_fallback",
    "success_no_errors",
    "invalid_output",
    "error",
    "running",
    "blocked",
    "cancelled",
]


class ParallelFinding(TypedDict):
    """Contribuição independente produzida por uma branch de análise."""

    source: str
    findings: list[str]


def merge_parallel_findings(
    left: list[ParallelFinding],
    right: list[ParallelFinding],
) -> list[ParallelFinding]:
    """
    Mantém uma contribuição por origem no fan-in.

    Sem este reducer, as duas branches paralelas escreveriam no mesmo campo e
    o LangGraph recusaria a atualização concorrente.
    """
    merged = {item["source"]: item for item in left}
    merged.update({item["source"]: item for item in right})
    return list(merged.values())


def merge_unique_strings(left: list[str], right: list[str]) -> list[str]:
    """Mescla histórico concorrente preservando ordem e unicidade."""
    return list(dict.fromkeys([*left, *right]))


class AgentState(TypedDict, total=False):
    """
    Estado compartilhado e de curta duração do JavaLog Agent.

    O estado é **mutado** pelos nós, que devolvem dicionários parciais; nunca
    é reatribuído. Os dois campos anotados com reducer são os únicos que
    recebem escrita concorrente.
    """

    # --- herdados do mini-projeto ---
    file_path: str
    log_content: str
    extracted_events: list[str]
    exceptions: list[str]
    category: str
    evidence: list[str]
    diagnostic: dict[str, Any]
    report_path: str
    status: AgentStatus
    error: str
    validation_errors: list[str]

    # --- correlação entre os sinais de observabilidade ---
    correlation_id: str
    audit_id: str
    request_source: Literal["cli", "api", "mcp", "test"]

    # --- memória curta isolada por thread ---
    thread_id: str
    memory_context: dict[str, Any]

    # --- segurança e limites de autonomia ---
    security_flags: list[str]
    redacted: bool
    requires_human: bool
    blocked_reason: str
    cancel_requested: bool

    # --- controle de fluxo e parada ---
    current_step: int
    max_steps: int
    llm_attempts: int

    # --- paralelização: únicos campos com escrita concorrente ---
    parallel_findings: Annotated[
        list[ParallelFinding],
        merge_parallel_findings,
    ]
    node_history: Annotated[list[str], merge_unique_strings]

    # --- métricas da execução ---
    started_at: float
    latency_ms: float
    http_status: int
    observability_errors: list[str]

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# Mensagem de recusa. É comparada caractere a caractere, com acentuação, pelo
# teste de aceitação do cenário adversarial.
BLOQUEIO_MENSAGEM = "Ação não autorizada bloqueada; aprovação humana necessária."
LIBERACAO_MENSAGEM = "Nenhum conteúdo hostil detectado na entrada."

# Substituto único de qualquer valor sensível. O valor original nunca é
# devolvido, registrado nem guardado em estado.
REDACTED = "[REDACTED]"

# As três famílias de conteúdo hostil reconhecidas.
FAMILIA_PROMPT_INJECTION = "prompt_injection"
FAMILIA_SECRET_REQUEST = "secret_request"
FAMILIA_EXTERNAL_ACTION = "external_action_request"

FAMILIAS = (
    FAMILIA_PROMPT_INJECTION,
    FAMILIA_SECRET_REQUEST,
    FAMILIA_EXTERNAL_ACTION,
)

# Teto do conteúdo não confiável repassado adiante. Entrada externa não define
# quanto contexto consome.
LIMITE_CONTEUDO_NAO_CONFIAVEL = 4000

# Fragmentos de credenciais são montados em runtime para não gerar falsos
# alertas na varredura do próprio código.

_PREFIXO_OPENAI = "sk"
_PREFIXOS_PROVEDOR = "|".join(
    p + "_" for p in ("ghp", "gho", "ghu", "ghs", "ghr", "github_pat")
)
_ESQUEMA_PORTADOR = "Bea" + "rer"

# Evita falsos positivos quando `sk` integra um identificador.
_INICIO_ISOLADO = r"(?<![A-Za-z0-9_])"

# Aceita tokens compostos e consome o valor integral.
_COMPONENTES = r"(?:[A-Za-z0-9]+[-_])*"

_NOMES_DE_SEGREDO = (
    r"(?:api[_\-\s]?key|apikey|access[_\-\s]?token|token|secret|password"
    r"|passwd|senha|credential|credencial)"
)

_PADROES_REDACAO = (
    # Credencial de provedor, reconhecida pelo prefixo.
    re.compile(
        _INICIO_ISOLADO
        + _PREFIXO_OPENAI
        + r"[-_]"
        + _COMPONENTES
        + r"[A-Za-z0-9]{16,}"
    ),
    re.compile(
        _INICIO_ISOLADO + r"(?:" + _PREFIXOS_PROVEDOR + r")[A-Za-z0-9_]{10,}"
    ),
    # Reconhece o esquema portador sem distinguir maiúsculas de minúsculas.
    re.compile(_ESQUEMA_PORTADOR + r"\s+[A-Za-z0-9._~+/=\-]{10,}", re.IGNORECASE),
)

# Atribuição `nome = valor`: o NOME é preservado, só o valor é substituído.
# Preservar o nome mantém a linha legível para diagnóstico sem expor nada.
_PADRAO_ATRIBUICAO = re.compile(
    _NOMES_DE_SEGREDO + r"(\s*[:=]\s*)([\"']?)([A-Za-z0-9_\-./+]{8,})",
    re.IGNORECASE,
)


def _compilar(*padroes: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in padroes)


# Exige alvo explícito para diferenciar prompt injection de texto operacional.
_PADROES_PROMPT_INJECTION = _compilar(
    r"ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instruction",
    r"disregard\s+(?:all\s+|the\s+)?(?:previous\s+)?(?:instruction|rule)",
    r"ignore\s+(?:as\s+|todas\s+as\s+)?(?:instru|regras)",
    r"desconsidere\s+(?:as\s+|todas\s+as\s+|o\s+)?(?:instru|regras|prompt)",
    r"esque[cç]a\s+(?:as\s+|todas\s+as\s+)?(?:instru|regras)",
    r"(?:system|developer)\s+prompt",
    r"override\s+(?:your\s+|the\s+)?(?:instruction|rule|system|polic)",
    r"new\s+instructions\s*:",
    r"novas\s+instru\w*\s*:",
    r"you\s+are\s+now\s+(?:a|an|the)\s",
    r"voc[eê]\s+agora\s+[ée]\s+(?:um|uma|o|a)\s",
    r"act\s+as\s+(?:an?\s+)?(?:unrestricted|different|developer|admin)",
)

# Exige verbo de solicitação para não bloquear menções legítimas a credenciais.
_PADROES_SECRET_REQUEST = _compilar(
    r"(?:reveal|print|show|dump|send|expose|leak|give\s+me)\s+"
    r"(?:me\s+)?(?:the\s+|your\s+|all\s+)?"
    r"(?:api[_\-\s]?key|apikey|secret|token|password|credential|env\b)",
    r"(?:mostre|revele|exiba|imprima|envie|informe)\s+"
    r"(?:me\s+)?(?:a\s+|o\s+|as\s+|os\s+|sua\s+|seu\s+)?"
    r"(?:chave|senha|token|segredo|credenc)",
    r"what\s+is\s+(?:your\s+|the\s+)?"
    r"(?:api[_\-\s]?key|apikey|secret|token|password)",
    r"qual\s+(?:[ée]\s+)?(?:a\s+|o\s+|sua\s+|seu\s+)?"
    r"(?:chave|senha|token|segredo)",
)

# Pedido de ação fora dos limites do agente: sair para a rede, apagar dados,
# executar comando de sistema.
_PADROES_EXTERNAL_ACTION = _compilar(
    r"(?:send|post|upload|forward|exfiltrate|leak)\b[^\n]{0,60}?https?://",
    r"(?:envie|poste|publique|mande|exfiltre)\b[^\n]{0,60}?https?://",
    r"\bcurl\s+(?:-|https?://)",
    r"\bwget\s+https?://",
    r"\brm\s+-rf\b",
    r"\bdrop\s+table\b",
    r"\bdelete\s+(?:all|every|the\s+entire)\b",
    r"(?:apague|delete|remova|destrua)\s+(?:todos|tudo|todas|o\s+banco)",
    r"webhook\.site",
    r"\bshutdown\s+(?:-|now\b)",
)

_PADROES_POR_FAMILIA: dict[str, tuple[re.Pattern[str], ...]] = {
    FAMILIA_PROMPT_INJECTION: _PADROES_PROMPT_INJECTION,
    FAMILIA_SECRET_REQUEST: _PADROES_SECRET_REQUEST,
    FAMILIA_EXTERNAL_ACTION: _PADROES_EXTERNAL_ACTION,
}


class PolicyDecision(BaseModel):
    """
    Veredito da política de autonomia sobre um conteúdo não confiável.

    O modelo é **congelado** e não carrega o conteúdo avaliado: a decisão
    circula pelo estado e pelos sinais, e nada do que foi inspecionado viaja
    junto dela.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    status: Literal["allowed", "blocked"]
    flags: tuple[str, ...]
    requires_human: bool
    message: str


def detect_families(content: object) -> tuple[str, ...]:
    """
    Devolve as famílias hostis presentes no conteúdo, na ordem canônica.

    Entrada que não seja string é tratada como conteúdo vazio: a política não
    levanta exceção diante de estado incompleto, porque uma falha aqui viraria
    caminho de escape para o que ela deveria bloquear.
    """
    if not isinstance(content, str) or not content:
        return ()

    return tuple(
        familia
        for familia in FAMILIAS
        if any(padrao.search(content) for padrao in _PADROES_POR_FAMILIA[familia])
    )


def evaluate_policy(content: object) -> PolicyDecision:
    """
    Aplica a política de autonomia ao conteúdo não confiável.

    Função **pura**: inspeciona e decide, sem alterar o texto recebido e sem
    redigir coisa alguma. Redigir é atribuição de `redact_sensitive_text`, e a
    separação é deliberada — quem decide não reescreve.

    Qualquer família detectada bloqueia e exige aprovação humana. Não há
    gradação: o agente não tem autonomia para julgar quão hostil é um pedido
    que já identificou como hostil.
    """
    flags = detect_families(content)

    if flags:
        return PolicyDecision(
            allowed=False,
            status="blocked",
            flags=flags,
            requires_human=True,
            message=BLOQUEIO_MENSAGEM,
        )

    return PolicyDecision(
        allowed=True,
        status="allowed",
        flags=(),
        requires_human=False,
        message=LIBERACAO_MENSAGEM,
    )


def _substituir_atribuicao(correspondencia: re.Match[str]) -> str:
    """Preserva o nome, o separador e a aspa; troca apenas o valor."""
    inicio = correspondencia.start(1) - correspondencia.start(0)
    nome = correspondencia.group(0)[:inicio]
    aspa = correspondencia.group(2)
    return f"{nome}{correspondencia.group(1)}{aspa}{REDACTED}"


def redact_sensitive_text(text: object) -> str:
    """
    Substitui qualquer valor sensível por `[REDACTED]`.

    O valor original não é devolvido, registrado nem guardado: a função troca
    e descarta. Em atribuições o nome da chave é preservado, para que a linha
    continue diagnosticável sem expor o valor.
    """
    if not isinstance(text, str) or not text:
        return ""

    redigido = text
    for padrao in _PADROES_REDACAO:
        redigido = padrao.sub(REDACTED, redigido)
    return _PADRAO_ATRIBUICAO.sub(_substituir_atribuicao, redigido)


def contains_secret(text: object) -> bool:
    """Indica se a redação alteraria o texto, sem revelar o que foi achado."""
    return isinstance(text, str) and redact_sensitive_text(text) != text


def sanitize_untrusted_content(content: object, limite: int | None = None) -> str:
    """
    Prepara conteúdo externo para seguir adiante: redigido e com teto.

    Defesa em profundidade, não a defesa principal — o que barra um conteúdo
    hostil é `evaluate_policy`. Esta função existe para o caso em que algo
    passe: mesmo então, nenhum segredo atravessa e nenhuma entrada externa
    define sozinha quanto contexto consome.
    """
    teto = LIMITE_CONTEUDO_NAO_CONFIAVEL if limite is None else limite
    redigido = redact_sensitive_text(content)
    return redigido[:teto] if len(redigido) > teto else redigido


def sanitize_memory_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Redige o contexto de memória antes que ele seja reaproveitado.

    Devolve um dicionário **novo**: o original não é alterado. Um segredo
    presente numa execução anterior da thread não reaparece no prompt, no
    relatório nem na resposta da execução seguinte.
    """
    if not context:
        return context

    sanitizado = dict(context)
    if "summary" in sanitizado:
        sanitizado["summary"] = redact_sensitive_text(sanitizado["summary"])
    if "evidence" in sanitizado:
        sanitizado["evidence"] = [
            redact_sensitive_text(item) for item in sanitizado["evidence"]
        ]
    return sanitizado

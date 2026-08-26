from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

# Mensagens centralizadas para manter estável o contrato de validação.
THREAD_ID_VAZIO_MENSAGEM = (
    "thread_id não pode ser vazio nem conter apenas espaços."
)
THREAD_ID_TIPO_MENSAGEM = "thread_id deve ser uma string."


def create_checkpointer() -> InMemorySaver:
    """
    Cria o checkpointer da memória curta do agente.

    `InMemorySaver` guarda o estado **no processo**, indexado por `thread_id`.
    A escolha é deliberada e está justificada no plano: o contexto relevante
    ao domínio é o que a própria thread já concluiu sobre logs relacionados,
    não um corpus externo — por isso não há RAG, nem base vetorial, nem
    persistência em disco. Persistir estado de diagnóstico entre processos
    criaria superfície de dados sensíveis sem ganho funcional.

    O limite é assumido, não escondido: encerrado o processo, a memória some.
    """
    return InMemorySaver()


def normalize_thread_id(thread_id: Any) -> str:
    """
    Normaliza o identificador da thread ou recusa a entrada.

    `"  sessao-1  "` e `"sessao-1"` designam a MESMA thread — sem o `.strip()`
    o LangGraph as trataria como duas, e a segunda invocação não encontraria
    nada do que a primeira gravou. Já uma string vazia, ou só com espaços, não
    identifica coisa alguma: em vez de silenciosamente virar uma thread nova a
    cada chamada, é recusada na entrada.

    As duas recusas são de naturezas diferentes e por isso têm exceções
    diferentes: string vazia é um **valor** inaceitável (`ValueError`), tipo
    não-string é um erro de **programação** de quem chamou (`TypeError`).
    """
    if not isinstance(thread_id, str):
        raise TypeError(THREAD_ID_TIPO_MENSAGEM)

    normalizado = thread_id.strip()
    if not normalizado:
        raise ValueError(THREAD_ID_VAZIO_MENSAGEM)
    return normalizado


def thread_config(thread_id: Any) -> dict[str, Any]:
    """
    Monta o `config` que o LangGraph usa para isolar a memória da thread.

    Este módulo monta a chave e cria o checkpointer; **não decide o que é
    memorizado** — essa decisão é dos nós, que sabem o que a execução produziu.
    """
    return {"configurable": {"thread_id": normalize_thread_id(thread_id)}}

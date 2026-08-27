from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from src.config import load_config
from src.memory import create_checkpointer, normalize_thread_id
from src.nodes import (
    analisar_eventos,
    analisar_excecoes,
    cancelar_execucao,
    consolidar_analises,
    escrever_relatorio,
    finalizar_execucao,
    gerar_resposta_erro,
    gerar_resposta_limite,
    gerar_resultado_sem_erros,
    inicializar_execucao,
    ler_log,
    make_diagnosticar,
    tratar_saida_invalida,
    validar_entrada,
    validar_saida,
    verificar_seguranca,
)
from src.state import AgentState

# Status terminais em que a resposta pública não deve expor campos vazios.
STATUS_SEM_DIAGNOSTICO = {"error", "cancelled", "blocked"}

# Campos que pertencem a UMA execução, e o valor com que cada um recomeça.
#
# Com checkpointer, a segunda invocação da mesma thread não parte do zero: ela
# parte do estado final da primeira. Isso é exatamente o que dá memória — e é
# também o que faria o diagnóstico, o relatório e o erro da execução anterior
# reaparecerem como se fossem da atual. A fachada zera aqui tudo o que é de
# uma execução só, e preserva `memory_context`, que é justamente o que deve
# atravessar. Só o que quem chama NÃO informou é zerado, de modo que a API e
# o MCP continuam podendo impor os próprios identificadores de correlação.
CAMPOS_POR_EXECUCAO: dict[str, Any] = {
    "log_content": "",
    "extracted_events": [],
    "exceptions": [],
    "category": "",
    "evidence": [],
    "diagnostic": {},
    "report_path": "",
    "error": "",
    "validation_errors": [],
    "security_flags": [],
    "redacted": False,
    "requires_human": False,
    "blocked_reason": "",
    "fallback_reason": "",
    "cancel_requested": False,
    "correlation_id": "",
    "audit_id": "",
    "started_at": 0.0,
    "current_step": 0,
    "llm_attempts": 0,
    "latency_ms": 0.0,
    "http_status": 0,
    "observability_errors": [],
}


def route_inicializar(state: AgentState) -> str:
    """
    Decide cancelamento, limite ou continuação antes de qualquer tool.

    A comparação é `>=`, não `>`: atingir o limite já encerra. Com `>` o
    passo de número `max_steps` ainda seria executado, e o limite valeria na
    prática como `max_steps + 1`.
    """
    if state.get("cancel_requested", False):
        return "cancelada"
    if state.get("current_step", 0) >= state.get("max_steps", 32):
        return "limite"
    return "continuar"


def route_validar_entrada(state: AgentState) -> str:
    """Decide o caminho após a validação da entrada."""
    if state.get("validation_errors") or state.get("error"):
        return "invalida"
    return "valida"


def route_ler_log(state: AgentState) -> list[str]:
    """
    Decide o caminho após tentar ler o log.

    Devolve uma **lista** de nós: no caminho feliz o fluxo se abre nas duas
    análises paralelas de uma vez. Essa forma é deliberada — a alternativa
    (aresta condicional para uma branch mais aresta incondicional para a
    outra) faria a segunda branch executar **também no caminho de erro**,
    sobre conteúdo que nunca foi lido.
    """
    if state.get("error"):
        return ["gerar_resposta_erro"]
    return ["analisar_excecoes", "analisar_eventos"]


def route_seguranca_e_categoria(state: AgentState) -> str:
    """Prioriza o bloqueio; depois decide entre log limpo e diagnóstico."""
    if state.get("requires_human"):
        return "bloqueada"
    if state.get("category", "Unknown") == "Clean":
        return "sem_erros"
    return "com_erros"


def route_validar_saida(state: AgentState) -> str:
    """Decide o caminho após validar a saída do diagnóstico."""
    return "invalida" if state.get("status") == "invalid_output" else "valida"


class JavaLogGraph:
    """
    Fachada do grafo compilado.

    Existe por um motivo único e explicável: injetar `thread_id` e limites de
    execução sem quebrar o contrato simples herdado do mini-projeto, em que a
    CLI chama `create_graph().invoke({"file_path": ...})` e nada mais.
    """

    def __init__(self, compiled_graph: Any):
        self._compiled_graph = compiled_graph

    def invoke(
        self,
        input_state: AgentState,
        config: dict[str, Any] | None = None,
    ) -> AgentState:
        """Completa o estado de entrada e normaliza a resposta pública."""
        state = dict(input_state)
        supplied_config = dict(config or {})
        configurable = dict(supplied_config.get("configurable", {}))

        # `thread_id` informado é normalizado e pode ser recusado; ausente,
        # ganha um identificador novo. A diferença importa: quem não informa
        # thread nenhuma quer uma execução isolada, enquanto quem informa uma
        # thread vazia informou algo que não identifica coisa alguma.
        fornecido = state.get("thread_id")
        if fornecido is None:
            fornecido = configurable.get("thread_id")

        thread_id = (
            str(uuid4()) if fornecido is None else normalize_thread_id(fornecido)
        )
        state["thread_id"] = thread_id

        for campo, valor_inicial in CAMPOS_POR_EXECUCAO.items():
            state.setdefault(campo, valor_inicial)

        state.setdefault("max_steps", load_config().max_steps)
        state.setdefault("request_source", "test")

        runtime_config: dict[str, Any] = {
            key: value
            for key, value in supplied_config.items()
            if key != "configurable"
        }
        # O `thread_id` escolhido e normalizado deve prevalecer sobre o valor
        # recebido em `configurable`. Os demais campos de configuração são
        # preservados.
        runtime_config["configurable"] = {
            **configurable,
            "thread_id": thread_id,
        }
        # Rede de segurança do próprio LangGraph, além do limite de passos.
        runtime_config.setdefault("recursion_limit", 64)

        result = dict(self._compiled_graph.invoke(state, runtime_config))

        # Nos desfechos sem diagnóstico, não devolver chaves vazias: o
        # contrato herdado do mini-projeto verifica a AUSÊNCIA das chaves.
        if result.get("status") in STATUS_SEM_DIAGNOSTICO:
            if not result.get("diagnostic"):
                result.pop("diagnostic", None)
            if not result.get("report_path"):
                result.pop("report_path", None)
        return result

    def get_state(self, config: dict[str, Any]):
        """Expõe o estado persistido, usado pela memória por thread (E04)."""
        return self._compiled_graph.get_state(config)

    def get_graph(self):
        """Expõe o grafo compilado, usado nas verificações de topologia."""
        return self._compiled_graph.get_graph()


def create_graph(llm=None, checkpointer=None) -> JavaLogGraph:
    """
    Cria e compila o StateGraph do agente.

    O LLM continua sendo injetado como dependência, exatamente como no
    mini-projeto: sem LLM fornecido, o nó de diagnóstico constrói um
    ChatOpenAI em tempo de execução.

    O checkpointer segue a mesma regra e é a memória curta da E04. Sem um
    fornecido, cada grafo recebe o seu — o que mantém o comportamento herdado
    de dois grafos distintos não se enxergarem. Compartilhar memória entre
    chamadas é decisão de quem monta o grafo: a API mantém um grafo único por
    processo, e por isso threads iguais se reencontram entre requisições.
    """
    workflow = StateGraph(AgentState)

    # --- nós de controle ---
    workflow.add_node("inicializar_execucao", inicializar_execucao)
    workflow.add_node("cancelar_execucao", cancelar_execucao)
    workflow.add_node("gerar_resposta_limite", gerar_resposta_limite)
    workflow.add_node("finalizar_execucao", finalizar_execucao)

    # --- nós herdados do mini-projeto ---
    workflow.add_node("validar_entrada", validar_entrada)
    workflow.add_node("gerar_resposta_erro", gerar_resposta_erro)
    workflow.add_node("ler_log", ler_log)
    workflow.add_node("gerar_resultado_sem_erros", gerar_resultado_sem_erros)
    workflow.add_node("diagnosticar", make_diagnosticar(llm))
    workflow.add_node("validar_saida", validar_saida)
    workflow.add_node("tratar_saida_invalida", tratar_saida_invalida)
    workflow.add_node("escrever_relatorio", escrever_relatorio)

    # --- branches paralelas e junção ---
    workflow.add_node("analisar_excecoes", analisar_excecoes)
    workflow.add_node("analisar_eventos", analisar_eventos)
    workflow.add_node("consolidar_analises", consolidar_analises)

    # --- governança: aplicada antes de qualquer decisão de diagnóstico ---
    workflow.add_node("verificar_seguranca", verificar_seguranca)

    # Ponto de entrada.
    workflow.add_edge(START, "inicializar_execucao")

    # Parada controlada antes de qualquer leitura ou chamada externa.
    workflow.add_conditional_edges(
        "inicializar_execucao",
        route_inicializar,
        {
            "cancelada": "cancelar_execucao",
            "limite": "gerar_resposta_limite",
            "continuar": "validar_entrada",
        },
    )
    workflow.add_edge("cancelar_execucao", "finalizar_execucao")
    workflow.add_edge("gerar_resposta_limite", "finalizar_execucao")

    # Validação da entrada.
    workflow.add_conditional_edges(
        "validar_entrada",
        route_validar_entrada,
        {
            "invalida": "gerar_resposta_erro",
            "valida": "ler_log",
        },
    )
    workflow.add_edge("gerar_resposta_erro", "finalizar_execucao")

    # FAN-OUT: a rota devolve a lista de destinos, abrindo as duas análises.
    workflow.add_conditional_edges(
        "ler_log",
        route_ler_log,
        ["gerar_resposta_erro", "analisar_excecoes", "analisar_eventos"],
    )

    # FAN-IN: só executa quando AS DUAS branches concluírem.
    workflow.add_edge(
        ["analisar_excecoes", "analisar_eventos"],
        "consolidar_analises",
    )

    # A política roda entre o fan-in e a decisão: nenhuma chamada ao modelo e
    # nenhuma escrita acontecem antes dela.
    workflow.add_edge("consolidar_analises", "verificar_seguranca")

    # Decisão entre bloqueio, log limpo e diagnóstico.
    workflow.add_conditional_edges(
        "verificar_seguranca",
        route_seguranca_e_categoria,
        {
            "bloqueada": "finalizar_execucao",
            "sem_erros": "gerar_resultado_sem_erros",
            "com_erros": "diagnosticar",
        },
    )

    workflow.add_edge("gerar_resultado_sem_erros", "escrever_relatorio")
    workflow.add_edge("diagnosticar", "validar_saida")

    workflow.add_conditional_edges(
        "validar_saida",
        route_validar_saida,
        {
            "invalida": "tratar_saida_invalida",
            "valida": "escrever_relatorio",
        },
    )
    workflow.add_edge("tratar_saida_invalida", "escrever_relatorio")

    # Término único: TODAS as rotas convergem para cá antes do END.
    workflow.add_edge("escrever_relatorio", "finalizar_execucao")
    workflow.add_edge("finalizar_execucao", END)

    return JavaLogGraph(
        workflow.compile(checkpointer=checkpointer or create_checkpointer())
    )

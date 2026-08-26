from langgraph.graph import END, START, StateGraph

from src.nodes import (
    classificar_log,
    escrever_relatorio,
    extrair_eventos,
    gerar_resposta_erro,
    gerar_resultado_sem_erros,
    ler_log,
    make_diagnosticar,
    tratar_saida_invalida,
    validar_entrada,
    validar_saida,
)
from src.state import AgentState


def route_validar_entrada(state: AgentState) -> str:
    """Decide o caminho após a validação da entrada."""
    errors = state.get("validation_errors", [])
    if errors:
        return "invalida"
    return "valida"


def route_ler_log(state: AgentState) -> str:
    """Decide o caminho após tentar ler o log."""
    error = state.get("error")
    if error:
        return "erro_leitura"
    return "sucesso"


def route_classificar_log(state: AgentState) -> str:
    """Decide o caminho após classificar o log."""
    category = state.get("category", "Unknown")
    if category == "Clean":
        return "sem_erros"
    return "com_erros"


def route_validar_saida(state: AgentState) -> str:
    """Decide o caminho após validar a saída do diagnóstico."""
    status = state.get("status")
    if status == "invalid_output":
        return "invalida"
    return "valida"


def create_graph(llm=None):
    """
    Cria e compila o StateGraph do agente.

    O LLM é injetado como dependência do nó de diagnóstico. Sem LLM
    fornecido, o nó constrói um ChatOpenAI em tempo de execução.
    """
    workflow = StateGraph(AgentState)

    # Adicionar nós
    workflow.add_node("validar_entrada", validar_entrada)
    workflow.add_node("gerar_resposta_erro", gerar_resposta_erro)
    workflow.add_node("ler_log", ler_log)
    workflow.add_node("extrair_eventos", extrair_eventos)
    workflow.add_node("classificar_log", classificar_log)
    workflow.add_node("gerar_resultado_sem_erros", gerar_resultado_sem_erros)
    workflow.add_node("diagnosticar", make_diagnosticar(llm))
    workflow.add_node("validar_saida", validar_saida)
    workflow.add_node("tratar_saida_invalida", tratar_saida_invalida)
    workflow.add_node("escrever_relatorio", escrever_relatorio)

    # Ponto de entrada com a constante START
    workflow.add_edge(START, "validar_entrada")

    # Arestas condicionais a partir da validação de entrada
    workflow.add_conditional_edges(
        "validar_entrada",
        route_validar_entrada,
        {
            "invalida": "gerar_resposta_erro",
            "valida": "ler_log",
        },
    )

    # Aresta de erro de entrada para o fim
    workflow.add_edge("gerar_resposta_erro", END)

    # Roteamento condicional após leitura do log
    workflow.add_conditional_edges(
        "ler_log",
        route_ler_log,
        {
            "erro_leitura": "gerar_resposta_erro",
            "sucesso": "extrair_eventos",
        },
    )

    # Fluxo linear de extração e classificação
    workflow.add_edge("extrair_eventos", "classificar_log")

    # Arestas condicionais a partir da classificação
    workflow.add_conditional_edges(
        "classificar_log",
        route_classificar_log,
        {
            "sem_erros": "gerar_resultado_sem_erros",
            "com_erros": "diagnosticar",
        },
    )

    # Caminho sem erros
    workflow.add_edge("gerar_resultado_sem_erros", "escrever_relatorio")

    # Caminho com erros
    workflow.add_edge("diagnosticar", "validar_saida")

    # Arestas condicionais a partir da validação de saída
    workflow.add_conditional_edges(
        "validar_saida",
        route_validar_saida,
        {
            "invalida": "tratar_saida_invalida",
            "valida": "escrever_relatorio",
        },
    )

    # Fallback direciona para escrita do relatório
    workflow.add_edge("tratar_saida_invalida", "escrever_relatorio")

    # Fim do fluxo normal
    workflow.add_edge("escrever_relatorio", END)

    return workflow.compile()

"""
Testes do fluxo LangGraph evoluído: rotas, paralelização e parada.

Complementam `test_routing.py`, herdado do mini-projeto, que continua
cobrindo os desfechos originais. Aqui o alvo é o que a evolução acrescentou.
"""

from unittest.mock import patch

import pytest

from src.graph import (
    JavaLogGraph,
    create_graph,
    route_inicializar,
    route_ler_log,
    route_seguranca_e_categoria,
    route_validar_entrada,
    route_validar_saida,
)
from src.nodes import CANCELAMENTO_MENSAGEM, LIMITE_MENSAGEM
from src.state import merge_parallel_findings, merge_unique_strings
from tests.fake_llm import FakeLLM

LOG_COM_ERRO = "ERROR Falhou\njava.lang.NullPointerException: teste"
LOG_LIMPO = "2026-07-18 INFO App started successfully"


class ContandoLLM(FakeLLM):
    """FakeLLM com contador, para provar que o modelo NÃO foi chamado.

    Subclasse local em vez de alteração no `fake_llm.py` herdado: a contagem
    interessa só a estes testes de parada.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.call_count = 0

    def invoke(self, input_data, config=None):
        self.call_count += 1
        return super().invoke(input_data, config)


@pytest.fixture
def graph():
    """Grafo sem LLM injetado."""
    return create_graph()


# --------------------------------------------------------------- compilação


def test_grafo_compila_e_devolve_fachada(graph):
    """O grafo compila e é entregue pela fachada, não cru."""
    assert isinstance(graph, JavaLogGraph)
    assert graph.get_graph() is not None


def test_todos_os_nos_previstos_existem(graph):
    """A topologia declara exatamente os nós previstos para a etapa."""
    nos = set(graph.get_graph().nodes)
    esperados = {
        "inicializar_execucao",
        "cancelar_execucao",
        "gerar_resposta_limite",
        "finalizar_execucao",
        "validar_entrada",
        "gerar_resposta_erro",
        "ler_log",
        "analisar_excecoes",
        "analisar_eventos",
        "consolidar_analises",
        "gerar_resultado_sem_erros",
        "diagnosticar",
        "validar_saida",
        "tratar_saida_invalida",
        "escrever_relatorio",
    }
    assert esperados.issubset(nos)


# ------------------------------------------------------ rotas, uma a uma


def test_route_inicializar_cancelamento():
    assert route_inicializar({"cancel_requested": True}) == "cancelada"


def test_route_inicializar_limite_acima():
    assert route_inicializar({"current_step": 33, "max_steps": 32}) == "limite"


def test_route_inicializar_limite_na_igualdade():
    """Atingir o limite já encerra: a comparação é `>=`, não `>`.

    Com `>`, o passo de número `max_steps` ainda executaria e o limite
    valeria na prática como `max_steps + 1`.
    """
    assert route_inicializar({"current_step": 32, "max_steps": 32}) == "limite"


def test_route_inicializar_continua_um_passo_antes_do_limite():
    """O passo imediatamente anterior ao limite ainda continua."""
    assert route_inicializar({"current_step": 31, "max_steps": 32}) == "continuar"


def test_route_inicializar_continuar():
    assert route_inicializar({"current_step": 1, "max_steps": 32}) == "continuar"


def test_route_validar_entrada_invalida_por_erro_de_validacao():
    assert route_validar_entrada({"validation_errors": ["x"]}) == "invalida"


def test_route_validar_entrada_invalida_por_erro_previo():
    assert route_validar_entrada({"error": "falhou"}) == "invalida"


def test_route_validar_entrada_valida():
    assert route_validar_entrada({"validation_errors": []}) == "valida"


def test_route_ler_log_erro_nao_abre_as_branches():
    """No erro de leitura, NENHUMA análise paralela é disparada."""
    destinos = route_ler_log({"error": "falha de leitura"})
    assert destinos == ["gerar_resposta_erro"]
    assert "analisar_eventos" not in destinos
    assert "analisar_excecoes" not in destinos


def test_route_ler_log_sucesso_abre_as_duas_branches():
    """No caminho feliz, o fan-out dispara as duas de uma vez."""
    assert route_ler_log({}) == ["analisar_excecoes", "analisar_eventos"]


def test_route_seguranca_bloqueada():
    """A rota de bloqueio existe desde já; passa a ser alcançada na E05."""
    assert route_seguranca_e_categoria({"requires_human": True}) == "bloqueada"


def test_route_seguranca_sem_erros():
    assert route_seguranca_e_categoria({"category": "Clean"}) == "sem_erros"


def test_route_seguranca_com_erros():
    assert route_seguranca_e_categoria({"category": "Code"}) == "com_erros"


def test_route_validar_saida_invalida():
    assert route_validar_saida({"status": "invalid_output"}) == "invalida"


def test_route_validar_saida_valida():
    assert route_validar_saida({"status": "success"}) == "valida"


# --------------------------------------------------- fan-out / fan-in


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_fan_in_preserva_as_duas_contribuicoes(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """As duas branches contribuem e nenhuma sobrescreve a outra."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (True, LOG_COM_ERRO)
    mock_write.return_value = (True, "output/report_error.log.md")

    final_state = graph.invoke({"file_path": "error.log"})

    origens = sorted(
        item["source"] for item in final_state["parallel_findings"]
    )
    assert origens == ["eventos", "excecoes"]
    assert len(final_state["parallel_findings"]) == 2


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_historico_registra_os_dois_nos_paralelos(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """O histórico de nós prova que ambas as branches executaram."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (True, LOG_COM_ERRO)
    mock_write.return_value = (True, "output/report_error.log.md")

    final_state = graph.invoke({"file_path": "error.log"})

    historico = final_state["node_history"]
    assert "analisar_excecoes" in historico
    assert "analisar_eventos" in historico
    assert "consolidar_analises" in historico


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_branches_nao_executam_no_erro_de_leitura(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Falha de leitura não dispara análise sobre conteúdo inexistente."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (False, "Erro ao ler arquivo de log")

    final_state = graph.invoke({"file_path": "valid.log"})

    historico = final_state["node_history"]
    assert "analisar_excecoes" not in historico
    assert "analisar_eventos" not in historico
    assert final_state["status"] == "error"
    mock_write.assert_not_called()


def test_reducer_mantem_uma_contribuicao_por_origem():
    """O reducer do fan-in não duplica origem nem perde contribuição."""
    esquerda = [{"source": "excecoes", "findings": ["a"]}]
    direita = [{"source": "eventos", "findings": ["b"]}]
    juntos = merge_parallel_findings(esquerda, direita)
    assert sorted(i["source"] for i in juntos) == ["eventos", "excecoes"]
    assert esquerda == [{"source": "excecoes", "findings": ["a"]}]


def test_reducer_do_historico_deduplica_preservando_ordem():
    assert merge_unique_strings(["a", "b"], ["b", "c"]) == ["a", "b", "c"]


# ------------------------------------------------------- parada controlada


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_cancelamento_encerra_sem_ler_nem_escrever(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Cancelamento encerra antes de qualquer leitura, escrita ou LLM."""
    final_state = graph.invoke(
        {"file_path": "error.log", "cancel_requested": True}
    )

    assert final_state["status"] == "cancelled"
    assert final_state["error"] == CANCELAMENTO_MENSAGEM
    assert "diagnostic" not in final_state
    mock_validate.assert_not_called()
    mock_read.assert_not_called()
    mock_write.assert_not_called()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_limite_de_passos_encerra_de_forma_controlada(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Limite muito ultrapassado termina sem repetição indefinida."""
    final_state = graph.invoke(
        {"file_path": "error.log", "current_step": 50, "max_steps": 10}
    )

    assert final_state["status"] == "error"
    assert final_state["error"] == LIMITE_MENSAGEM
    assert final_state["blocked_reason"] == "max_steps"
    mock_read.assert_not_called()
    mock_write.assert_not_called()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_limite_de_passos_encerra_exatamente_na_fronteira(
    mock_validate,
    mock_read,
    mock_write,
):
    """A execução para no passo em que o limite é atingido, não depois.

    `inicializar_execucao` incrementa `current_step` antes da rota. Entrando
    com 9 e limite 10, o passo vira 10 e a rota precisa encerrar ali. Um
    LLM é injetado para provar que ele também não é acionado.
    """
    llm = ContandoLLM()
    final_state = create_graph(llm=llm).invoke(
        {"file_path": "error.log", "current_step": 9, "max_steps": 10}
    )

    assert final_state["current_step"] == 10
    assert final_state["status"] == "error"
    assert final_state["blocked_reason"] == "max_steps"
    assert final_state["error"] == LIMITE_MENSAGEM
    assert "gerar_resposta_limite" in final_state["node_history"]
    assert "diagnostic" not in final_state

    mock_validate.assert_not_called()
    mock_read.assert_not_called()
    mock_write.assert_not_called()
    assert llm.call_count == 0


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_um_passo_antes_do_limite_a_execucao_prossegue(
    mock_validate,
    mock_read,
    mock_write,
):
    """Do outro lado da fronteira o fluxo segue normalmente."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (True, LOG_LIMPO)
    mock_write.return_value = (True, "output/report_clean.log.md")

    final_state = create_graph().invoke(
        {"file_path": "clean.log", "current_step": 8, "max_steps": 10}
    )

    assert final_state["current_step"] == 9
    assert final_state["status"] == "success_no_errors"
    assert "gerar_resposta_limite" not in final_state["node_history"]
    mock_read.assert_called_once()


# ----------------------------------------- término único e propagação


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
@pytest.mark.parametrize(
    ("entrada", "valido", "conteudo"),
    [
        ({"file_path": "error.log"}, True, LOG_COM_ERRO),
        ({"file_path": "clean.log"}, True, LOG_LIMPO),
        ({"file_path": "invalid.exe"}, False, ""),
        ({"file_path": "x.log", "cancel_requested": True}, True, LOG_LIMPO),
    ],
)
def test_toda_rota_passa_pelo_termino_unico(
    mock_validate,
    mock_read,
    mock_write,
    entrada,
    valido,
    conteudo,
):
    """Todas as rotas convergem para `finalizar_execucao` antes do END."""
    mock_validate.return_value = (valido, [] if valido else ["Inválido"])
    mock_read.return_value = (True, conteudo)
    mock_write.return_value = (True, "output/report.md")

    final_state = create_graph().invoke(entrada)

    assert "finalizar_execucao" in final_state["node_history"]
    assert final_state["status"] != "running"


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_correlacao_e_latencia_propagam_entre_os_nos(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Valor escrito na abertura chega ao término, sem reatribuição."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (True, LOG_LIMPO)
    mock_write.return_value = (True, "output/report_clean.log.md")

    final_state = graph.invoke({"file_path": "clean.log"})

    assert final_state["correlation_id"]
    assert final_state["audit_id"]
    assert final_state["correlation_id"] != final_state["audit_id"]
    assert final_state["latency_ms"] >= 0
    assert final_state["current_step"] == 1


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_thread_id_informado_e_preservado(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """A fachada respeita o `thread_id` recebido e gera um quando ausente."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (True, LOG_LIMPO)
    mock_write.return_value = (True, "output/report_clean.log.md")

    com_thread = graph.invoke(
        {"file_path": "clean.log", "thread_id": "thread-fixa"}
    )
    assert com_thread["thread_id"] == "thread-fixa"

    sem_thread = create_graph().invoke({"file_path": "clean.log"})
    assert sem_thread["thread_id"]
    assert sem_thread["thread_id"] != "thread-fixa"

"""
Testes da memória curta isolada por `thread_id` (E04).

A estratégia sob teste é state + checkpointer `InMemorySaver`, sem RAG. O que
precisa ficar provado aqui é o que o enunciado cobra: que a segunda invocação
da mesma thread **recupera** contexto da primeira, que threads distintas não
se enxergam, que o contexto recuperado é **limitado** e que um `thread_id`
que não identifica nada é recusado na entrada.
"""

from unittest.mock import patch

import pytest

from src.graph import CAMPOS_POR_EXECUCAO, create_graph
from src.memory import (
    THREAD_ID_TIPO_MENSAGEM,
    THREAD_ID_VAZIO_MENSAGEM,
    create_checkpointer,
    normalize_thread_id,
    thread_config,
)
from src.nodes import (
    MEMORY_EVIDENCIA_MAX_CARACTERES,
    MEMORY_MAX_EVIDENCIAS,
    MEMORY_RESUMO_MAX_CARACTERES,
    MEMORY_TRUNCAMENTO_SUFIXO,
    build_memory_context,
    formatar_memoria_para_prompt,
    truncar_para_memoria,
)
from tests.fake_llm import FakeLLM

LOG_COM_ERRO = "ERROR Falhou\njava.lang.NullPointerException: teste"
LOG_LIMPO = "2026-07-18 INFO App started successfully"


class LLMQueRegistraPrompt(FakeLLM):
    """FakeLLM que guarda o prompt recebido, para inspecionar o contexto."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts: list[str] = []

    def invoke(self, input_data, config=None):
        self.prompts.append(str(input_data))
        return super().invoke(input_data, config)


@pytest.fixture
def executar():
    """
    Devolve uma função que roda o grafo sem tocar em disco, rede ou modelo.

    O grafo é criado **uma vez** por fixture, de propósito: é o mesmo grafo,
    e portanto o mesmo checkpointer, que dá memória entre invocações. Um
    grafo novo a cada chamada esconderia justamente o que se quer provar.
    """
    llm = LLMQueRegistraPrompt()
    graph = create_graph(llm=llm)
    entregue: dict = {}

    invoke_do_compilado = graph._compiled_graph.invoke

    def espiao(state, cfg=None, **kwargs):
        """Guarda o `config` que a fachada realmente entrega ao grafo.

        É esse dicionário — e não o que a fachada devolve — que define sob
        qual chave o checkpointer grava. Sem observá-lo, um `thread_id`
        normalizado no estado e cru na persistência passaria despercebido.
        """
        entregue["config"] = cfg
        return invoke_do_compilado(state, cfg, **kwargs)

    def _executar(estado, conteudo=LOG_COM_ERRO, valido=True, config=None):
        with (
            patch("src.nodes.validate_log_file") as mock_validate,
            patch("src.nodes.read_log_file") as mock_read,
            patch("src.nodes.write_diagnostic_report") as mock_write,
            patch.object(graph._compiled_graph, "invoke", espiao),
        ):
            mock_validate.return_value = (
                (True, []) if valido else (False, ["Arquivo vazio: x.log"])
            )
            mock_read.return_value = (True, conteudo)
            mock_write.return_value = (True, "output/report_x.log.md")
            return graph.invoke(estado, config)

    _executar.llm = llm
    _executar.graph = graph
    _executar.entregue = entregue
    return _executar


# ------------------------------------------------- V044/V045: `thread_id`


@pytest.mark.parametrize("vazio", ["", "   ", "\t", "\n  \t "])
def test_thread_id_vazio_ou_so_espacos_e_recusado(vazio):
    """V044 — um identificador que não identifica nada não passa."""
    with pytest.raises(ValueError) as erro:
        thread_config(vazio)

    assert str(erro.value) == THREAD_ID_VAZIO_MENSAGEM


@pytest.mark.parametrize("errado", [None, 123, 1.5, b"t1", ["t1"], {"id": 1}])
def test_thread_id_de_tipo_errado_levanta_type_error(errado):
    """
    Tipo errado é `TypeError`, e não o mesmo `ValueError` da string vazia.

    A distinção é útil a quem chama: string vazia é um valor que chegou
    errado da fronteira, tipo não-string é um defeito de programação.
    """
    with pytest.raises(TypeError) as erro:
        thread_config(errado)

    assert str(erro.value) == THREAD_ID_TIPO_MENSAGEM


def test_thread_id_com_espacos_nas_bordas_e_normalizado():
    """V045 — as bordas somem e a chave é a mesma."""
    assert normalize_thread_id("  sessao-1  ") == "sessao-1"
    assert thread_config("  sessao-1  ") == thread_config("sessao-1")
    assert thread_config("sessao-1") == {
        "configurable": {"thread_id": "sessao-1"}
    }


def test_thread_config_devolve_apenas_a_chave_da_thread():
    """O config carrega o identificador e nada mais."""
    config = thread_config("sessao-1")

    assert list(config) == ["configurable"]
    assert list(config["configurable"]) == ["thread_id"]


def test_create_checkpointer_devolve_instancia_nova_a_cada_chamada():
    """Dois checkpointers distintos não compartilham memória."""
    primeiro = create_checkpointer()
    segundo = create_checkpointer()

    assert primeiro is not segundo


# ------------------------------------------- V046: limites do contexto


def test_truncamento_conta_o_sufixo_dentro_do_limite():
    """O limite é o total: 20 devolve 20 caracteres, não 23."""
    resultado = truncar_para_memoria("A" * 100, 20)

    assert len(resultado) == 20
    assert resultado.endswith(MEMORY_TRUNCAMENTO_SUFIXO)


def test_truncamento_preserva_texto_dentro_do_limite():
    """Abaixo do limite nada é cortado nem recebe sufixo."""
    resultado = truncar_para_memoria("curto", 20)

    assert resultado == "curto"
    assert not resultado.endswith(MEMORY_TRUNCAMENTO_SUFIXO)


def test_truncamento_no_limite_exato_nao_corta():
    """Fronteira: exatamente no limite ainda é texto inteiro."""
    texto = "A" * 20

    assert truncar_para_memoria(texto, 20) == texto


def test_o_limite_de_evidencias_previsto_e_dois():
    """
    O número está no contrato, não só na constante.

    Um teste que comparasse `len(evidence)` com `MEMORY_MAX_EVIDENCIAS` seria
    cego: subir a constante para 4 alteraria os dois lados da igualdade ao
    mesmo tempo e o teste continuaria verde. O `2` fica escrito aqui.
    """
    assert MEMORY_MAX_EVIDENCIAS == 2


def test_contexto_limita_a_duas_evidencias_e_truncadas():
    """V046 — no máximo duas evidências, cada uma dentro do limite."""
    contexto = build_memory_context({
        "category": "Code",
        "status": "success",
        "diagnostic": {"summary": "Resumo do diagnóstico."},
        "evidence": ["E" * 500, "F" * 500, "G" * 500, "H" * 500],
    })

    assert len(contexto["evidence"]) == 2
    assert contexto["evidence"][0].startswith("E")
    assert contexto["evidence"][1].startswith("F")
    for item in contexto["evidence"]:
        assert len(item) <= MEMORY_EVIDENCIA_MAX_CARACTERES
        assert item.endswith(MEMORY_TRUNCAMENTO_SUFIXO)


def test_contexto_trunca_o_resumo_longo():
    """Um resumo longo do modelo não entra inteiro na memória."""
    contexto = build_memory_context({
        "category": "Code",
        "status": "success",
        "diagnostic": {"summary": "R" * 2000},
    })

    assert len(contexto["summary"]) == MEMORY_RESUMO_MAX_CARACTERES
    assert contexto["summary"].endswith(MEMORY_TRUNCAMENTO_SUFIXO)


def test_contexto_expoe_exatamente_os_quatro_campos_previstos():
    """
    O contrato é fechado: categoria, resumo, status e evidências.

    O conteúdo bruto do log e a stack trace completa não entram — o que não
    é reaproveitado não pode vazar para um prompt.
    """
    contexto = build_memory_context({
        "category": "Code",
        "status": "success",
        "diagnostic": {"summary": "Resumo."},
        "evidence": ["evidencia"],
        "log_content": "SEGREDO NO CONTEUDO BRUTO DO LOG",
        "file_path": "examples/logs/x.log",
        "report_path": "output/report_x.log.md",
    })

    assert set(contexto) == {"category", "summary", "status", "evidence"}
    assert "SEGREDO NO CONTEUDO BRUTO DO LOG" not in str(contexto)
    assert "output/report_x.log.md" not in str(contexto)


def test_contexto_de_execucao_sem_diagnostico_guarda_o_erro():
    """Nas rotas de erro a thread se lembra de ter falhado."""
    contexto = build_memory_context({
        "status": "error",
        "error": "Arquivo vazio: x.log",
    })

    assert contexto["status"] == "error"
    assert contexto["summary"] == "Arquivo vazio: x.log"
    assert contexto["category"] == "Unknown"
    assert contexto["evidence"] == []


def test_memoria_ausente_nao_produz_bloco_de_prompt():
    """Sem memória, o prompt da primeira execução fica inalterado."""
    assert formatar_memoria_para_prompt(None) == ""
    assert formatar_memoria_para_prompt({}) == ""


# ---------------------------------- V042/V043: recuperação e isolamento


def test_segunda_invocacao_da_mesma_thread_recupera_o_contexto(executar):
    """V042 — T12: o contexto da primeira execução chega à segunda."""
    primeira = executar({"file_path": "a.log", "thread_id": "sessao-1"})
    assert primeira["memory_context"]["status"] == "success"

    executar({"file_path": "b.log", "thread_id": "sessao-1"})

    prompt_da_segunda = executar.llm.prompts[-1]
    assert "Contexto recuperado da execução anterior" in prompt_da_segunda
    assert "Fake LLM diagnostic summary" in prompt_da_segunda


def test_primeira_invocacao_nao_traz_contexto_anterior(executar):
    """Controle negativo: sem execução anterior, não há bloco de contexto."""
    executar({"file_path": "a.log", "thread_id": "sessao-unica"})

    assert "Contexto recuperado" not in executar.llm.prompts[-1]


def test_thread_distinta_nao_enxerga_nada_da_outra(executar):
    """V043 — T13: nenhum dado cruzado entre threads."""
    executar({"file_path": "a.log", "thread_id": "sessao-A"})
    executar({"file_path": "b.log", "thread_id": "sessao-B"})

    prompt_da_thread_b = executar.llm.prompts[-1]
    assert "Contexto recuperado" not in prompt_da_thread_b


def test_thread_normalizada_reencontra_a_memoria_da_mesma_thread(executar):
    """V045 — as bordas não criam uma thread nova."""
    executar({"file_path": "a.log", "thread_id": "sessao-1"})
    executar({"file_path": "b.log", "thread_id": "   sessao-1   "})

    assert "Contexto recuperado" in executar.llm.prompts[-1]


def test_memoria_nao_atravessa_grafos_distintos():
    """Cada grafo tem o seu checkpointer: memória não vaza entre eles."""
    with (
        patch("src.nodes.validate_log_file") as mock_validate,
        patch("src.nodes.read_log_file") as mock_read,
        patch("src.nodes.write_diagnostic_report") as mock_write,
    ):
        mock_validate.return_value = (True, [])
        mock_read.return_value = (True, LOG_COM_ERRO)
        mock_write.return_value = (True, "output/report_x.log.md")

        create_graph(llm=FakeLLM()).invoke(
            {"file_path": "a.log", "thread_id": "sessao-1"}
        )

        outro_llm = LLMQueRegistraPrompt()
        create_graph(llm=outro_llm).invoke(
            {"file_path": "b.log", "thread_id": "sessao-1"}
        )

    assert "Contexto recuperado" not in outro_llm.prompts[-1]


def test_thread_id_vazio_e_recusado_tambem_pela_fachada(executar):
    """A recusa vale no caminho real, não só na função isolada."""
    with pytest.raises(ValueError) as erro:
        executar({"file_path": "a.log", "thread_id": "   "})

    assert str(erro.value) == THREAD_ID_VAZIO_MENSAGEM


def test_sem_thread_id_cada_invocacao_e_isolada(executar):
    """Sem thread informada, o identificador é novo e não há memória."""
    primeira = executar({"file_path": "a.log"})
    segunda = executar({"file_path": "b.log"})

    assert primeira["thread_id"] != segunda["thread_id"]
    assert "Contexto recuperado" not in executar.llm.prompts[-1]


# ------------------------- o que a memória NÃO pode arrastar entre execuções


def test_segunda_execucao_com_erro_nao_devolve_o_relatorio_da_primeira(
    executar,
):
    """
    O que atravessa a thread é o contexto, não o resultado inteiro.

    Sem a limpeza dos campos de uma execução só, a segunda invocação
    responderia com o `diagnostic` e o `report_path` da primeira — um
    resultado da execução anterior apresentado como se fosse o desta.
    """
    primeira = executar({"file_path": "a.log", "thread_id": "sessao-1"})
    assert primeira["diagnostic"]["diagnostic_mode"] == "llm"

    segunda = executar(
        {"file_path": "vazio.log", "thread_id": "sessao-1"},
        valido=False,
    )

    assert segunda["status"] == "error"
    assert "diagnostic" not in segunda
    assert "report_path" not in segunda
    assert segunda["error"] == "Arquivo vazio: x.log"


def test_segunda_execucao_recebe_correlacao_e_contagem_proprias(executar):
    """Cada execução da thread é uma execução, com identidade própria."""
    primeira = executar({"file_path": "a.log", "thread_id": "sessao-1"})
    segunda = executar({"file_path": "b.log", "thread_id": "sessao-1"})

    assert segunda["correlation_id"] != primeira["correlation_id"]
    assert segunda["audit_id"] != primeira["audit_id"]
    assert segunda["current_step"] == primeira["current_step"] == 1


def test_cancelamento_anterior_nao_cancela_a_execucao_seguinte(executar):
    """Um `cancel_requested` da execução anterior não sobrevive a ela."""
    primeira = executar(
        {"file_path": "a.log", "thread_id": "sessao-1", "cancel_requested": True}
    )
    assert primeira["status"] == "cancelled"

    segunda = executar({"file_path": "b.log", "thread_id": "sessao-1"})

    assert segunda["status"] == "success"


def test_correlacao_informada_por_quem_chama_e_respeitada(executar):
    """A limpeza zera o que não foi informado, e só isso."""
    final = executar({
        "file_path": "a.log",
        "thread_id": "sessao-1",
        "correlation_id": "correlacao-da-api",
        "audit_id": "auditoria-da-api",
    })

    assert final["correlation_id"] == "correlacao-da-api"
    assert final["audit_id"] == "auditoria-da-api"


def test_memory_context_nao_esta_entre_os_campos_zerados():
    """O contrato da limpeza, explícito: a memória é o que sobrevive."""
    assert "memory_context" not in CAMPOS_POR_EXECUCAO
    assert "thread_id" not in CAMPOS_POR_EXECUCAO
    assert "diagnostic" in CAMPOS_POR_EXECUCAO
    assert "report_path" in CAMPOS_POR_EXECUCAO


# -------------------------- thread_id fornecido pelo config
#
# Estes testes verificam que o identificador público é o mesmo usado para
# indexar o checkpoint, incluindo normalização e precedência.


def test_thread_id_vindo_so_do_config_chega_normalizado_ao_checkpointer(
    executar,
):
    """(a) Bordas informadas pelo config não chegam à chave de persistência."""
    final = executar(
        {"file_path": "a.log"},
        config={"configurable": {"thread_id": "  sessao-config  "}},
    )

    assert final["thread_id"] == "sessao-config"
    entregue = executar.entregue["config"]["configurable"]["thread_id"]
    assert entregue == "sessao-config"

    # O checkpoint existe sob a chave normalizada, e NÃO sob a crua.
    assert executar.graph.get_state(thread_config("sessao-config")).values
    assert not executar.graph.get_state(
        {"configurable": {"thread_id": "  sessao-config  "}}
    ).values


def test_config_com_e_sem_bordas_compartilham_a_mesma_memoria(executar):
    """(b) `sessao-x` e `  sessao-x  ` pelo config são a MESMA thread."""
    executar(
        {"file_path": "a.log"},
        config={"configurable": {"thread_id": "sessao-compartilhada"}},
    )
    executar(
        {"file_path": "b.log"},
        config={"configurable": {"thread_id": "  sessao-compartilhada  "}},
    )

    assert "Contexto recuperado" in executar.llm.prompts[-1]
    assert "Fake LLM diagnostic summary" in executar.llm.prompts[-1]


def test_thread_id_do_estado_prevalece_sobre_o_do_config(executar):
    """(c) O estado decide — na resposta pública e na chave do checkpointer."""
    final = executar(
        {"file_path": "a.log", "thread_id": "  do-estado  "},
        config={"configurable": {"thread_id": "do-config"}},
    )

    assert final["thread_id"] == "do-estado"
    entregue = executar.entregue["config"]["configurable"]["thread_id"]
    assert entregue == "do-estado"

    assert executar.graph.get_state(thread_config("do-estado")).values
    assert not executar.graph.get_state(thread_config("do-config")).values


def test_demais_campos_do_configurable_sao_preservados(executar):
    """(d) Só o `thread_id` é decidido pela fachada; o resto passa intacto."""
    executar(
        {"file_path": "a.log", "thread_id": "sessao-1"},
        config={
            "configurable": {
                "thread_id": "ignorado",
                "checkpoint_ns": "namespace-do-chamador",
                "campo_livre": 42,
            },
            "recursion_limit": 99,
        },
    )

    configurable = executar.entregue["config"]["configurable"]
    assert configurable["thread_id"] == "sessao-1"
    assert configurable["checkpoint_ns"] == "namespace-do-chamador"
    assert configurable["campo_livre"] == 42
    assert executar.entregue["config"]["recursion_limit"] == 99


def test_thread_id_vazio_no_config_e_recusado(executar):
    """A recusa vale também no caminho do config, não só no do estado."""
    with pytest.raises(ValueError) as erro:
        executar(
            {"file_path": "a.log"},
            config={"configurable": {"thread_id": "   "}},
        )

    assert str(erro.value) == THREAD_ID_VAZIO_MENSAGEM

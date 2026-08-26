from unittest.mock import patch

import pytest

from src.graph import create_graph
from tests.fake_llm import FakeLLM


@pytest.fixture
def graph():
    """Grafo sem LLM injetado."""
    return create_graph()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_error(mock_validate, mock_read, mock_write, graph):
    """Entrada inválida encerra sem leitura, escrita ou LLM."""
    mock_validate.return_value = (False, ["Extensão inválida"])

    final_state = graph.invoke({"file_path": "invalid.exe"})

    assert final_state["status"] == "error"
    assert "Extensão inválida" in final_state["error"]
    assert "diagnostic" not in final_state
    mock_read.assert_not_called()
    mock_write.assert_not_called()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_success_no_errors(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Log limpo usa diagnóstico determinístico."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (
        True,
        "2026-07-18 INFO App started successfully",
    )
    mock_write.return_value = (
        True,
        "output/report_clean.log.md",
    )

    final_state = graph.invoke({"file_path": "clean.log"})

    assert final_state["status"] == "success_no_errors"
    assert final_state["diagnostic"]["diagnostic_mode"] == "deterministic"
    assert final_state["diagnostic"]["category"] == "Clean"
    mock_write.assert_called_once()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_success(mock_validate, mock_read, mock_write):
    """Saída válida do LLM segue para validação e relatório."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (
        True,
        "ERROR Failed\njava.lang.NullPointerException: test",
    )
    mock_write.return_value = (
        True,
        "output/report_error.log.md",
    )

    graph = create_graph(llm=FakeLLM())
    final_state = graph.invoke({"file_path": "error.log"})

    assert final_state["status"] == "success"
    assert final_state["diagnostic"]["diagnostic_mode"] == "llm"
    assert (
        final_state["diagnostic"]["summary"]
        == "Fake LLM diagnostic summary"
    )
    mock_write.assert_called_once()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_success_fallback_llm_failure(
    mock_validate,
    mock_read,
    mock_write,
):
    """Falha do LLM ativa fallback determinístico."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (
        True,
        "ERROR Failed\njava.lang.NullPointerException: test",
    )
    mock_write.return_value = (
        True,
        "output/report_error.log.md",
    )

    graph = create_graph(llm=FakeLLM(should_fail=True))
    final_state = graph.invoke({"file_path": "error.log"})

    assert final_state["status"] == "success_fallback"
    assert final_state["diagnostic"]["diagnostic_mode"] == "fallback"
    assert "NullPointerException" in final_state["diagnostic"]["exception"]
    assert final_state["error"] == ""
    mock_write.assert_called_once()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_success_fallback_no_api_key(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Ausência da chave de API ativa fallback determinístico."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (
        True,
        "ERROR Failed\njava.lang.NullPointerException: test",
    )
    mock_write.return_value = (
        True,
        "output/report_error.log.md",
    )

    with patch.dict("os.environ", {}, clear=True):
        final_state = graph.invoke({"file_path": "error.log"})

    assert final_state["status"] == "success_fallback"
    assert final_state["diagnostic"]["diagnostic_mode"] == "fallback"
    assert "NullPointerException" in final_state["diagnostic"]["exception"]
    assert final_state["error"] == ""
    mock_write.assert_called_once()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_invalid_llm_output(
    mock_validate,
    mock_read,
    mock_write,
):
    """Saída inválida do LLM ativa fallback determinístico."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (
        True,
        "ERROR Failed\njava.lang.NullPointerException: test",
    )
    mock_write.return_value = (
        True,
        "output/report_error.log.md",
    )

    graph = create_graph(llm=FakeLLM(invalid_output=True))
    final_state = graph.invoke({"file_path": "error.log"})

    assert final_state["status"] == "success_fallback"
    assert final_state["diagnostic"]["diagnostic_mode"] == "fallback"
    assert final_state["error"] == ""
    mock_write.assert_called_once()


@patch("src.nodes.write_diagnostic_report")
@patch("src.nodes.read_log_file")
@patch("src.nodes.validate_log_file")
def test_route_read_failure(
    mock_validate,
    mock_read,
    mock_write,
    graph,
):
    """Falha de leitura encerra com erro e não escreve relatório."""
    mock_validate.return_value = (True, [])
    mock_read.return_value = (
        False,
        "Erro ao ler arquivo de log",
    )

    final_state = graph.invoke({"file_path": "valid.log"})

    assert final_state["status"] == "error"
    assert "Erro ao ler arquivo de log" in final_state["error"]
    assert "diagnostic" not in final_state
    mock_write.assert_not_called()

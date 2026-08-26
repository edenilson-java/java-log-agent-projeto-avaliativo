from pathlib import Path

import pytest

from src import tools


def test_sanitize_report_name_normalizes_filename():
    result = tools.sanitize_report_name("relatorio final.md")

    assert result == "relatorio_final.md"


@pytest.mark.parametrize(
    "filename",
    [
        "",
        "   ",
        "../report.md",
        "subdir/report.md",
        r"subdir\report.md",
    ],
)
def test_sanitize_report_name_rejects_unsafe_names(filename):
    with pytest.raises(ValueError):
        tools.sanitize_report_name(filename)


def test_extract_log_events_deduplicates_results():
    content = (
        "ERROR Application failed\n"
        "WARN Connection is slow\n"
        "ERROR Application failed\n"
        "java.lang.NullPointerException: test\n"
        "java.lang.NullPointerException: test\n"
    )

    result = tools.extract_log_events(content)

    assert result["events"] == [
        "ERROR Application failed",
        "WARN Connection is slow",
    ]
    assert result["exceptions"] == [
        "java.lang.NullPointerException: test",
    ]


def test_read_log_file_reads_allowed_file(tmp_path, monkeypatch):
    logs_dir = tmp_path / "examples" / "logs"
    logs_dir.mkdir(parents=True)

    log_file = logs_dir / "application.log"
    log_file.write_text(
        "INFO Application started\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tools, "LOGS_DIR", logs_dir.resolve())

    success, content = tools.read_log_file(
        "examples/logs/application.log"
    )

    assert success is True
    assert content == "INFO Application started\n"


def test_read_log_file_blocks_path_outside_logs(tmp_path, monkeypatch):
    logs_dir = tmp_path / "examples" / "logs"
    logs_dir.mkdir(parents=True)

    outside_file = tmp_path / "outside.log"
    outside_file.write_text("ERROR outside\n", encoding="utf-8")

    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tools, "LOGS_DIR", logs_dir.resolve())

    success, message = tools.read_log_file("outside.log")

    assert success is False
    assert "Acesso negado" in message


def test_write_diagnostic_report_writes_only_to_output(
    tmp_path,
    monkeypatch,
):
    output_dir = (tmp_path / "output").resolve()
    monkeypatch.setattr(tools, "OUTPUT_DIR", output_dir)

    success, report_path = tools.write_diagnostic_report(
        "diagnostic.md",
        "# Diagnostic\n",
    )

    saved_file = Path(report_path)

    assert success is True
    assert saved_file == output_dir / "diagnostic.md"
    assert saved_file.read_text(encoding="utf-8") == "# Diagnostic\n"


def test_write_diagnostic_report_blocks_unsafe_name(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        tools,
        "OUTPUT_DIR",
        (tmp_path / "output").resolve(),
    )

    success, message = tools.write_diagnostic_report(
        "../diagnostic.md",
        "# Diagnostic\n",
    )

    assert success is False
    assert "caracteres inseguros" in message


# ---------------------------------------------------------------------------
# Portabilidade do caminho devolvido em saida publica (E03).
#
# Acrescentado apos teste de mutacao: reverter `as_posix()` para
# `str(target_path)` passava despercebido pela suite versionada, sendo pego
# apenas pelo script de verificacao, que nao e' entregue.
# ---------------------------------------------------------------------------


def test_write_diagnostic_report_devolve_caminho_portatil(
    tmp_path,
    monkeypatch,
):
    """O caminho devolvido nunca traz o separador do Windows."""
    monkeypatch.setattr(tools, "OUTPUT_DIR", (tmp_path / "output").resolve())

    sucesso, caminho = tools.write_diagnostic_report(
        "relatorio.md",
        "# Diagnostic\n",
    )

    assert sucesso is True
    assert "\\" not in caminho
    assert caminho.endswith("/relatorio.md")


def test_read_log_as_response_devolve_caminho_portatil(monkeypatch):
    """O contrato estruturado também normaliza o separador."""
    monkeypatch.setattr(
        tools,
        "read_log_file",
        lambda _: (True, "conteudo"),
    )

    entrada_windows = r"examples\logs\arquivo.log"
    resposta = tools.read_log_as_response(entrada_windows)

    assert "\\" not in resposta.file_path
    assert resposta.file_path == "examples/logs/arquivo.log"


# ---------------------------------------------------------------------------
# Tipo errado na funcao interna (E03, apos auditoria).
#
# A funcao interna e' chamada tambem por caminhos que NAO passam por schema
# Pydantic — a tool MCP e qualquer chamador direto. Antes desta correcao,
# `read_log_as_response(123)` levantava TypeError em vez de devolver o
# contrato de erro exigido por V030.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entrada",
    [123, None, ["examples/logs/x.log"], {"file_path": "x.log"}, 1.5, b"x.log"],
)
def test_read_log_as_response_recusa_tipo_errado_sem_levantar(entrada):
    """Tipo errado vira contrato de erro, nunca exceção."""
    resposta = tools.read_log_as_response(entrada)

    assert resposta.status == "error"
    assert resposta.file_path == ""
    assert resposta.content == ""
    assert resposta.size_bytes == 0
    assert resposta.truncated is False
    assert resposta.error == tools.TIPO_INVALIDO_MENSAGEM


def test_read_log_as_response_tipo_errado_nao_le_nem_escreve(monkeypatch):
    """Nenhuma leitura e nenhuma escrita para entrada de tipo errado."""
    chamadas = []
    monkeypatch.setattr(
        tools, "read_log_file", lambda *a: chamadas.append("leu") or (True, "x")
    )
    monkeypatch.setattr(
        tools,
        "write_diagnostic_report",
        lambda *a: chamadas.append("escreveu") or (True, "x"),
    )

    tools.read_log_as_response(123)

    assert chamadas == []

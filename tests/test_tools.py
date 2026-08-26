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

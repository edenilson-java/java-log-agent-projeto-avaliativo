
from src.validation import MAX_FILE_SIZE_BYTES, validate_log_file


def test_rejects_missing_file_path(tmp_path):
    is_valid, errors = validate_log_file(
        "",
        base_dir=str(tmp_path),
    )

    assert is_valid is False
    assert errors == ["Caminho do arquivo não fornecido."]


def test_accepts_valid_log_file(tmp_path):
    log_file = tmp_path / "application.log"
    log_file.write_text("INFO Application started\n", encoding="utf-8")

    is_valid, errors = validate_log_file(
        str(log_file),
        base_dir=str(tmp_path),
    )

    assert is_valid is True
    assert errors == []


def test_accepts_valid_txt_file(tmp_path):
    log_file = tmp_path / "application.txt"
    log_file.write_text("INFO Application started\n", encoding="utf-8")

    is_valid, errors = validate_log_file(
        str(log_file),
        base_dir=str(tmp_path),
    )

    assert is_valid is True
    assert errors == []


def test_rejects_invalid_extension(tmp_path):
    invalid_file = tmp_path / "application.exe"
    invalid_file.write_text("content\n", encoding="utf-8")

    is_valid, errors = validate_log_file(
        str(invalid_file),
        base_dir=str(tmp_path),
    )

    assert is_valid is False
    assert any("Extensão inválida" in error for error in errors)


def test_rejects_nonexistent_file(tmp_path):
    missing_file = tmp_path / "missing.log"

    is_valid, errors = validate_log_file(
        str(missing_file),
        base_dir=str(tmp_path),
    )

    assert is_valid is False
    assert any("Arquivo não encontrado" in error for error in errors)


def test_rejects_empty_file(tmp_path):
    empty_file = tmp_path / "empty.log"
    empty_file.touch()

    is_valid, errors = validate_log_file(
        str(empty_file),
        base_dir=str(tmp_path),
    )

    assert is_valid is False
    assert any("arquivo está vazio" in error.lower() for error in errors)


def test_rejects_file_above_size_limit(tmp_path):
    large_file = tmp_path / "large.log"

    with large_file.open("wb") as file:
        file.truncate(MAX_FILE_SIZE_BYTES + 1)

    is_valid, errors = validate_log_file(
        str(large_file),
        base_dir=str(tmp_path),
    )

    assert is_valid is False
    assert any("tamanho máximo" in error for error in errors)


def test_rejects_file_outside_base_directory(tmp_path):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    outside_file = tmp_path / "outside.log"
    outside_file.write_text("ERROR outside\n", encoding="utf-8")

    is_valid, errors = validate_log_file(
        str(outside_file),
        base_dir=str(allowed_dir),
    )

    assert is_valid is False
    assert any("Acesso negado" in error for error in errors)

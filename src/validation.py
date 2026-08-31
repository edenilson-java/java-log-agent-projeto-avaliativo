from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".log", ".txt"}


def validate_log_file(
    file_path: str,
    base_dir: str = "examples/logs",
) -> tuple[bool, list[str]]:
    """
    Valida caminho, existência, extensão, tamanho e conteúdo do log.

    A validação é determinística e não lê o conteúdo completo do arquivo.
    """
    if not file_path or not file_path.strip():
        return False, ["Caminho do arquivo não fornecido."]

    try:
        supplied_base = Path(base_dir)
        supplied_file = Path(file_path)

        if supplied_base.is_absolute():
            base_path = supplied_base.resolve()
        else:
            base_path = (PROJECT_ROOT / supplied_base).resolve()

        if supplied_file.is_absolute():
            target_path = supplied_file.resolve()
        else:
            target_path = (PROJECT_ROOT / supplied_file).resolve()

        if not target_path.is_relative_to(base_path):
            return (
                False,
                [
                    (
                        "Acesso negado. O arquivo deve estar dentro de "
                        f"{base_dir}."
                    )
                ],
            )

        if not target_path.exists() or not target_path.is_file():
            return (
                False,
                ["Arquivo não encontrado ou não é um arquivo regular."],
            )

        errors: list[str] = []

        if target_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            errors.append(
                f"Extensão inválida. Permitidas: {allowed}."
            )

        file_size = target_path.stat().st_size

        if file_size > MAX_FILE_SIZE_BYTES:
            errors.append(
                "Arquivo excede o tamanho máximo permitido de "
                f"{MAX_FILE_SIZE_MB} MB."
            )

        if file_size == 0:
            errors.append("O arquivo está vazio.")

        return len(errors) == 0, errors

    except OSError as exc:
        return False, [f"Erro ao validar arquivo: {exc}"]

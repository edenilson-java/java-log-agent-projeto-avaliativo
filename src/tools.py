import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = (PROJECT_ROOT / "examples" / "logs").resolve()
OUTPUT_DIR = (PROJECT_ROOT / "output").resolve()

ALLOWED_LOG_SUFFIXES = {".log", ".txt"}
MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024


def read_log_file(file_path: str) -> tuple[bool, str]:
    """
    Lê um arquivo de log restrito ao diretório examples/logs.

    Valida caminho, extensão, existência, tipo, tamanho máximo
    e conteúdo não vazio.
    """
    try:
        supplied_path = Path(file_path)

        if supplied_path.is_absolute():
            target_path = supplied_path.resolve()
        else:
            target_path = (PROJECT_ROOT / supplied_path).resolve()

        if not target_path.is_relative_to(LOGS_DIR):
            return (
                False,
                (
                    "Acesso negado: o arquivo está fora do diretório "
                    f"permitido ({LOGS_DIR})."
                ),
            )

        if target_path.suffix.lower() not in ALLOWED_LOG_SUFFIXES:
            return (
                False,
                (
                    f"Extensão inválida: {target_path.suffix}. "
                    "Permitidas: .log e .txt."
                ),
            )

        if not target_path.exists():
            return False, f"Arquivo não encontrado: {file_path}"

        if not target_path.is_file():
            return False, f"Não é um arquivo regular: {file_path}"

        file_size = target_path.stat().st_size

        if file_size > MAX_LOG_SIZE_BYTES:
            return (
                False,
                (
                    f"Arquivo muito grande: {file_size} bytes. "
                    "Tamanho máximo permitido: 5 MB."
                ),
            )

        if file_size == 0:
            return False, f"Arquivo vazio: {file_path}"

        with target_path.open(
            mode="r",
            encoding="utf-8",
            errors="replace",
        ) as log_file:
            content = log_file.read()

        if not content.strip():
            return False, f"Arquivo vazio após leitura: {file_path}"

        return True, content
    except Exception as exc:  # noqa: BLE001 - fronteira de I/O
        return False, f"Erro ao ler arquivo de log: {exc}"


def sanitize_report_name(filename: str) -> str:
    """
    Sanitiza o nome de um relatório e impede path traversal.
    """
    if not filename or not filename.strip():
        raise ValueError("Nome do arquivo não pode estar vazio.")

    if "/" in filename or "\\" in filename:
        raise ValueError("Nome do arquivo não pode conter barras.")

    if ".." in filename:
        raise ValueError("Nome do arquivo não pode conter path traversal.")

    clean_name = Path(filename).stem
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name)
    clean_name = re.sub(r"_+", "_", clean_name)

    clean_name = clean_name.removesuffix("_md")

    clean_name = clean_name.strip("_").strip()

    if not clean_name:
        raise ValueError(
            "Nome do arquivo resulta em vazio após sanitização."
        )

    return f"{clean_name}.md"


def write_diagnostic_report(
    filename: str,
    content: str,
) -> tuple[bool, str]:
    """
    Grava um relatório Markdown restrito ao diretório output.
    """
    try:
        if not filename or not filename.strip():
            return False, "Nome do arquivo não pode estar vazio."

        if "/" in filename or "\\" in filename or ".." in filename:
            return False, "Nome do arquivo contém caracteres inseguros."

        safe_filename = sanitize_report_name(filename)
        target_path = (OUTPUT_DIR / safe_filename).resolve()

        if not target_path.is_relative_to(OUTPUT_DIR):
            return (
                False,
                (
                    "Acesso negado: tentativa de gravação fora do "
                    f"diretório permitido ({OUTPUT_DIR})."
                ),
            )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with target_path.open(
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as report_file:
            report_file.write(content)

        return True, str(target_path)
    except Exception as exc:  # noqa: BLE001 - fronteira de I/O
        return False, f"Erro ao gravar relatório: {exc}"


def extract_log_events(
    log_content: str,
) -> dict[str, list[str]]:
    """
    Extrai exceções Java e linhas de log ERROR ou WARN.
    """
    exceptions: list[str] = []
    events: list[str] = []

    exception_pattern = re.compile(
        r"([a-zA-Z0-9_.]+(?:Exception|Error)(?::\s*.*)?)$",
        re.MULTILINE,
    )

    event_pattern = re.compile(
        r"^[^\r\n]*?(?:ERROR|WARN)[ \t]+[^\r\n]*$",
        re.MULTILINE,
    )

    for match in exception_pattern.finditer(log_content):
        exception_text = match.group(1).strip()

        if exception_text not in exceptions:
            exceptions.append(exception_text)

    for match in event_pattern.finditer(log_content):
        event_text = match.group(0).strip()

        if event_text not in events:
            events.append(event_text)

    return {
        "exceptions": exceptions,
        "events": events,
    }

import argparse
import sys

from dotenv import load_dotenv

from src.graph import create_graph


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="JavaLog Agent - Diagnóstico de Logs Java/Spring Boot"
    )
    parser.add_argument(
        "file_path",
        help="Caminho para o arquivo de log a ser analisado",
    )

    args = parser.parse_args()
    file_path = args.file_path

    print(f"Iniciando análise do log: {file_path}")

    app = create_graph()
    initial_state = {"file_path": file_path}

    try:
        final_state = app.invoke(initial_state)

        status = final_state.get("status", "unknown")
        print(f"\nStatus Final: {status}")

        if status == "error":
            print(f"Erro: {final_state.get('error')}")
            sys.exit(1)

        report_path = final_state.get("report_path")
        if report_path:
            print(f"Relatório gerado com sucesso em: {report_path}")

        if final_state.get("diagnostic"):
            mode = final_state["diagnostic"].get("diagnostic_mode")
            print(f"Modo de diagnóstico: {mode}")

        sys.exit(0)

    except Exception as exc:  # noqa: BLE001 - fronteira da CLI
        print(f"\nErro crítico durante a execução do agente: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

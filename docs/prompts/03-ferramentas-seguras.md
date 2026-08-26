# Ferramentas seguras para análise de logs

**Tipo:** Prompt de implementação do bloco
**Arquivo relacionado:** `src/tools.py`
**Objetivo:** implementar capacidades mínimas e controladas para leitura de logs, extração de eventos e gravação de relatórios.

## Prompt utilizado

Implemente `src/tools.py` para o projeto JavaLog Agent em Python 3.12.

Requisitos:

- usar `pathlib.Path`;
- permitir leitura somente dentro de `examples/logs`;
- bloquear imediatamente caminhos fora do diretório autorizado;
- aceitar somente arquivos `.log` e `.txt`;
- validar existência, arquivo regular, conteúdo não vazio e tamanho máximo de 5 MB;
- ler em UTF-8 com substituição de caracteres inválidos;
- extrair exceções Java terminadas em `Exception` ou `Error`;
- extrair linhas de log com nível `ERROR` ou `WARN`;
- remover resultados duplicados preservando a ordem;
- sanitizar nomes de relatórios;
- impedir barras, `..` e path traversal na escrita;
- gravar relatórios somente dentro de `output`;
- usar UTF-8 e quebra de linha LF;
- retornar resultados pequenos e previsíveis;
- não executar shell, rede ou comandos externos;
- não adicionar capacidades além das necessárias.

A implementação deve fornecer:

- `read_log_file`;
- `extract_log_events`;
- `sanitize_report_name`;
- `write_diagnostic_report`.

## Validações realizadas

- compilação com `py_compile`;
- verificação de UTF-8 e LF;
- leitura de log permitido;
- bloqueio de path traversal;
- sanitização de nome de relatório;
- extração de exceções e eventos.

# Validação segura da entrada

**Tipo:** Prompt de implementação do bloco
**Arquivo relacionado:** `src/validation.py`
**Objetivo:** validar arquivos de log antes da leitura e impedir acesso fora do diretório autorizado.

## Prompt utilizado

Implemente `src/validation.py` para o projeto JavaLog Agent em Python 3.12.

Requisitos:

- usar `pathlib.Path`;
- receber o caminho do arquivo e o diretório-base permitido;
- rejeitar caminho vazio;
- resolver caminhos absolutos e relativos;
- permitir somente arquivos dentro de `examples/logs`;
- ao detectar arquivo fora do diretório permitido, retornar imediatamente;
- não consultar existência, tipo ou metadados de caminho externo;
- aceitar somente extensões `.log` e `.txt`;
- validar existência e arquivo regular;
- rejeitar arquivo vazio;
- limitar o tamanho máximo a 5 MB;
- retornar uma tupla com sucesso e lista de erros;
- manter comportamento determinístico;
- não ler o conteúdo completo do arquivo;
- não executar shell, rede ou comandos externos;
- não adicionar capacidades além das necessárias.

A implementação deve fornecer:

- `validate_log_file`.

## Validações realizadas

- compilação com `py_compile`;
- arquivo permitido aceito;
- path traversal bloqueado;
- retorno imediato para caminho externo;
- verificação de UTF-8;
- verificação de quebras de linha LF.

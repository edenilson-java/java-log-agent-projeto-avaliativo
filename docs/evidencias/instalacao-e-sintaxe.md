# Evidência — instalação, sintaxe e dependências

O que foi executado para confirmar que o projeto instala, compila e passa no lint.

## Ambiente

| Item | Valor |
|---|---|
| Interpretador | **Python 3.12.10** |
| Dependências declaradas | **12** em `requirements.txt` |
| Arquivos Python | **15** em `src/`, **15** em `tests/` |
| Chave de modelo | **ausente** durante todas as execuções abaixo |
| Rede externa | bloqueada nas execuções da suíte |

## Sintaxe

**Comando:** `python -m compileall -q src tests`
**Código de saída:** `0`

`compileall -q` só imprime quando encontra erro de sintaxe. Saída vazia com
código `0` significa que **todos** os arquivos das duas pastas compilam.

## Lint

```text
ruff check src tests   ->  All checks passed!
ruff check .           ->  All checks passed!
```

As duas invocações são conferidas de propósito. O pipeline de CI roda
`ruff check src tests` — o escopo do código do produto —, mas o repositório
inteiro também precisa passar, para que nenhum arquivo fora desse escopo carregue
problema silencioso.

## Dependências

**Comando:** `pip check`

```text
No broken requirements found.
```

Nenhuma dependência quebrada, nenhum conflito de versão. As 12 dependências de
`requirements.txt` são as **efetivamente usadas**: cada uma tem import
correspondente no código, e a varredura de recursos proibidos verifica os dois
lados — dependência sem import e import sem dependência.

## Instalação a partir do zero

A sequência de instalação do `README.md` para **Windows PowerShell** foi
executada como está escrita:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Depois disso, os quatro comandos de verificação rodam sem configuração adicional:

```text
pytest -q                        413 passed
ruff check src tests             All checks passed!
python -m compileall -q src      exit 0
pip check                        No broken requirements found
```

**Nenhum passo exige chave de modelo.** Copiar o `.env.example` para `.env` e
preencher a chave é opcional: sem ela, o agente conclui pelo caminho
determinístico. Essa é a diferença entre um projeto que *precisa* de credencial
para ser avaliado e um que **funciona inteiro sem ela**.

## Reprodução da automação low-code

Reproduzir o fluxo n8n exige **Node.js e npm/npx**, que são pré-requisitos de
outra natureza — não são dependências da aplicação. A CLI, a API e o servidor MCP
funcionam sem eles. As versões testadas e as sequências completas estão em
[`../low-code/reproducao.md`](../low-code/reproducao.md).

# Evidência — cenários de uso

Os dois cenários exigidos, executados pela CLI, com a saída literal e o código de
saída observados.

## Cenário 1 — log com exceção

**Comando:**

```bash
python -m src.main examples/logs/null-pointer-exception.log
```

**Saída real:**

```text
Iniciando análise do log: examples/logs/null-pointer-exception.log

Status Final: success_fallback
Relatório gerado com sucesso em: output/report_null-pointer-exception.md
Modo de diagnóstico: fallback
```

**Código de saída:** `0`

O caminho do relatório é **relativo e portátil** — `output/<nome>.md`. O caminho
absoluto governa o confinamento da escrita, mas não sai na resposta pública: ele
revelaria a raiz da máquina de quem executou e não serviria a quem consome o
resultado de outro lugar.

### Leitura

| O que a saída mostra | Significado |
|---|---|
| `Status Final: success_fallback` | o fluxo concluiu; o diagnóstico veio do caminho determinístico |
| `Modo de diagnóstico: fallback` | não havia chave de modelo configurada — o comportamento **esperado** nesse ambiente |
| relatório gerado | a escrita ocorreu, restrita a `output/` |

Com uma chave válida configurada, o mesmo comando produz `success` e
`Modo de diagnóstico: llm`. **A capacidade de concluir não depende da chave** —
depende dela apenas a qualidade da redação do diagnóstico.

## Cenário 2 — entrada adversarial

**Comando:**

```bash
python -m src.main examples/logs/adversarial-prompt-injection.log
```

**Saída real:**

```text
Iniciando análise do log: examples/logs/adversarial-prompt-injection.log

Status Final: blocked
Erro: Ação não autorizada bloqueada; aprovação humana necessária.
```

**Código de saída:** `1`

### Leitura

| O que a saída mostra | Significado |
|---|---|
| `Status Final: blocked` | a política de autonomia recusou prosseguir |
| a mensagem literal | é a mesma constante do código, sem paráfrase |
| código de saída `1` | a CLI **propaga** o bloqueio para quem a chamou — um script que encadeie o comando percebe a recusa |

**Nenhum relatório de diagnóstico foi gerado** e **nenhuma chamada ao modelo foi
realizada**. A execução bloqueada ainda registra uma linha em cada um dos dois
sinais de observabilidade, preservando a rastreabilidade da decisão. O bloqueio
acontece antes da decisão de diagnóstico, e nenhuma ação com efeito sobre o mundo
externo executa depois dele.

A fixture é **integralmente fictícia** e **não contém segredo**: os valores que
parecem credencial são sintéticos e a redação os devolve inalterados quando não
há segredo real. Ver
[`../seguranca/cenario-adversarial.md`](../seguranca/cenario-adversarial.md).

## Os dois lados da mesma proteção

Um bloqueio que dispara sobre log legítimo é tão inútil quanto um que não dispara:
o agente deixaria de diagnosticar qualquer coisa. Por isso os três logs legítimos
do projeto — `application-clean.log`, `bean-creation-error.log` e
`null-pointer-exception.log` — passam **sem** bloqueio, e isso é verificado por
teste versionado.

| Entrada | Desfecho | Código de saída |
|---|---|---|
| `null-pointer-exception.log` | `success_fallback`, relatório gerado | `0` |
| `bean-creation-error.log` | conclui e gera relatório | `0` |
| `application-clean.log` | `success_no_errors`, sem erro a diagnosticar | `0` |
| `adversarial-prompt-injection.log` | `blocked`, sem relatório gerado | `1` |

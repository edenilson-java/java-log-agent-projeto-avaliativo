# Evidência — observabilidade

Os dois sinais, correlacionados, gravados por duas execuções reais da CLI.

## Como foi produzido

```bash
python -m src.main examples/logs/null-pointer-exception.log
python -m src.main examples/logs/adversarial-prompt-injection.log
```

Sem chave de modelo e com acesso a rede externa bloqueado, a partir de sinais
vazios.

## Resultado

```text
output/agent-events.jsonl   2 linhas
output/agent-audit.jsonl    2 linhas
pares casados por correlation_id e audit_id: 2 de 2
```

**Uma linha por execução em cada sinal**, qualquer que tenha sido o desfecho.
Isso vale porque todas as rotas — sucesso, erro, bloqueio, cancelamento e limite
— passam pelo mesmo ponto único de término.

## O registro de auditoria

Tipado, sem campo livre. Recorte real das duas linhas, com os identificadores
abreviados:

```text
execucao 1
  stage           finalizar_execucao
  decision        diagnosed_by_fallback
  status          success_fallback
  error           Falha na geração do diagnóstico com LLM: OPENAI_API_KEY não configurada.
  correlation_id  44f86ae4…   audit_id d8aa3308…   latency_ms 8.657

execucao 2
  stage           finalizar_execucao
  decision        blocked_by_policy
  status          blocked
  error           Ação não autorizada bloqueada; aprovação humana necessária.
  correlation_id  df0f02d8…   audit_id 0c6fba21…   latency_ms 4.645
```

Duas leituras que só a auditoria permite:

**O fallback diz por quê.** `error` na auditoria carrega a **causa técnica** —
`OPENAI_API_KEY não configurada` — enquanto o `error` público da resposta
permanece vazio, porque para quem consome a API aquilo não é um erro: o
diagnóstico foi entregue. Sem esse campo, os quatro modos de falha do modelo
seriam indistinguíveis na investigação.

**O bloqueio é registrado.** Um bloqueio que não aparecesse nos sinais seria
invisível para quem investiga depois.

## O log de aplicação

Mesma correlação, com campo livre `details`. Campos presentes na primeira linha:

```text
category · current_step · llm_attempts · node_history · redacted
report_path · request_source · requires_human · security_flags · thread_id
```

**`http_status` não está presente** — e a ausência é deliberada. O campo existe no
estado, mas o código HTTP é decidido na fronteira, **depois** que o grafo retorna,
enquanto o sinal é emitido **dentro** do grafo. Publicá-lo faria toda linha
afirmar `http_status: 0`, um valor que contradiz a resposta efetivamente
devolvida. Omitir é honesto; zerar seria falso. O achado e a correção estão em
[`../qa/code-review-ia.md`](../qa/code-review-ia.md).

## Garantias verificadas por teste

| Garantia | Como é verificada |
|---|---|
| Correlação | `correlation_id` e `audit_id` iguais nos dois sinais e iguais ao estado final |
| Uma linha por execução | duas execuções → duas linhas em cada arquivo |
| Redação antes da escrita | credencial injetada no fluxo aparece como `[REDACTED]` nos dois sinais |
| Teto da causa | causa longa é truncada em 500 caracteres |
| Escrita serializada | trava de escrita impede linha corrompida por concorrência |
| Falha de gravação não derruba o fluxo | erro de escrita é acumulado no estado, a execução conclui |
| Isolamento entre execuções | a causa de uma execução não vaza para a seguinte da mesma thread |

Os arquivos `output/*.jsonl` são **gerados em tempo de execução** e permanecem
fora do conjunto versionável — `output/` entra no repositório vazio, apenas com o
`.gitkeep`.

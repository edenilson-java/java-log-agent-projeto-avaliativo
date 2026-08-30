# Evidência — testes

Contagem real da suíte, distribuição por arquivo e o que cada grupo cobre.

## Execução

**Comando:** `pytest -q`
**Ambiente:** sem chave de modelo e com acesso a rede externa bloqueado
**Código de saída:** `0`

```text
413 passed
```

Nenhum teste pulado, nenhum erro de coleta, nenhuma falha esperada. A ausência de
`s` na saída importa: suítes que crescem tendem a acumular testes ignorados por
condição de ambiente — "pula se não houver chave", "pula se não houver rede" — e
cada pulo transforma uma garantia em intenção. Aqui não há nenhum, porque o
caminho **sem chave e sem rede é o caminho normal** de execução, não um modo
degradado.

## Distribuição

| Arquivo | Testes | O que cobre |
|---|---:|---|
| `tests/test_security.py` | 98 | política de autonomia, três famílias de conteúdo hostil, redação de dez formatos de credencial |
| `tests/test_observability.py` | 56 | os dois sinais correlacionados, redação recursiva, todas as rotas, contrato de auditoria |
| `tests/test_memory.py` | 39 | isolamento por thread, limites do contexto, chave real do checkpointer |
| `tests/test_api.py` | 39 | fronteira HTTP e fronteira CLI |
| `tests/test_graph_advanced.py` | 32 | rotas, paralelização, condições de parada |
| `tests/test_n8n_workflow.py` | 29 | estrutura do fluxo low-code, ausência de credencial, reprodutibilidade |
| `tests/test_resilience.py` | 25 | quatro formas de falha do modelo e o fallback |
| `tests/test_mcp.py` | 22 | fronteira MCP, atravessando `call_tool` |
| `tests/test_tools.py` | 20 | leitura e escrita confinadas, portabilidade de caminho |
| `tests/test_devops.py` | 19 | métricas da série, recusa de série não rotulada, contrato do workflow de CI |
| `tests/test_config.py` | 19 | configuração tipada, imutável, sem vazamento da chave |
| `tests/test_validation.py` | 8 | validação de entrada herdada |
| `tests/test_routing.py` | 7 | roteamento herdado |
| **Total** | **413** | |

## Tipos de teste presentes

O item 4.7 do enunciado pede **ao menos um** entre integração, aceitação e E2E.
Os três estão presentes:

| Tipo | Onde | Exemplo |
|---|---|---|
| **Integração** | `tests/test_api.py`, `tests/test_mcp.py` | a API é exercitada por HTTP e o resultado é conferido contra o sinal gravado |
| **Aceitação** | `tests/test_security.py` | o cenário adversarial é executado ponta a ponta e o desfecho conferido contra o critério declarado |
| **E2E** | `tests/test_api.py`, seção de fronteira CLI | o comando roda inteiro e o código de saída é verificado |

Detalhamento em [`../qa/estrategia-testes.md`](../qa/estrategia-testes.md).

## O que a contagem não diz

`413 passed` mede **quantos testes existem e passaram**, não quanto do
comportamento eles observam. Um teste que se ancora na própria constante que
deveria proteger aparece nessa linha como mais um ponto verde.

Por isso a suíte foi medida por **campanhas de mutação** ao longo do projeto: o
comportamento é deliberadamente quebrado e se observa se algum teste falha. As
campanhas registradas somam **dezenas de mutações**, e os casos em que uma
mutação **sobreviveu** estão documentados como ciclos em
[`../evolucao-mini-projeto.md`](../evolucao-mini-projeto.md) — porque o valor da
técnica está justamente nos sobreviventes.

## Prioridade por risco

O cenário mais coberto é o **bloqueio adversarial**, por decisão explícita.
A ordem completa e a justificativa estão em
[`../qa/priorizacao-risco.md`](../qa/priorizacao-risco.md).

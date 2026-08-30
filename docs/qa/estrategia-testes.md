# Estratégia de testes

A suíte tem **345 testes**, executáveis sem chave de API e sem rede. Este
documento declara a que tipo cada arquivo pertence e por quê.

## O tipo que cumpre o mínimo exigido

**O tipo que cumpre o mínimo do item 4.7 do enunciado é o de integração.**

E2E e aceitação são **cobertura adicional**, acrescentada por decisão do
projeto — não por exigência. A declaração é explícita para que a avaliação não
precise inferir: se apenas um tipo tivesse de existir, seriam os testes de
integração.

## Classificação

| Arquivo | Testes | Tipo | O que caracteriza |
|---|---|---|---|
| `tests/test_api.py` | 38 | **Integração** | atravessa a fronteira HTTP real com `TestClient`; exercita o contrato, o mapeamento de status e a gravação dos sinais |
| `tests/test_mcp.py` | 22 | **Integração** | atravessa `server.call_tool(...)` — o caminho que um cliente MCP percorre — e não o handler isolado |
| `tests/test_graph_advanced.py` | 32 | **E2E** | invoca o grafo compilado de ponta a ponta, do início ao término único, cobrindo rotas, paralelização e parada |
| `tests/test_memory.py` | 39 | **E2E** | duas invocações completas na mesma thread, medindo o que atravessa e o que não atravessa entre execuções |
| `tests/test_observability.py` | 56 | **E2E** | executa o fluxo inteiro e depois lê os arquivos de sinal gravados em disco |
| `tests/test_resilience.py` | 25 | **E2E** | executa o fluxo inteiro sob quatro formas de falha do modelo e confere o desfecho e os sinais |
| `tests/test_security.py` | 98 | **Aceitação** | reproduz o critério do enunciado: a ação não autorizada é bloqueada, com a mensagem literal, sem chamada ao modelo e sem escrita |
| `tests/test_tools.py` | 20 | Unidade | funções da ferramenta isoladas |
| `tests/test_validation.py` | 8 | Unidade | validação determinística da entrada |
| `tests/test_routing.py` | 7 | Unidade | rotas do grafo com estado sintético, herdado do mini-projeto |

**Integração: 60 testes · E2E: 152 · Aceitação: 98 · Unidade: 35.**

## O que distingue os três tipos, neste projeto

A separação não é por tamanho do teste, e sim por **qual fronteira é
atravessada**.

**Integração** — o teste entra pela mesma porta que um cliente externo usaria:
uma requisição HTTP, ou uma chamada de tool pelo servidor MCP. O que se prova é
que o contrato da fronteira está correto: código de status, forma da resposta,
recusa de entrada malformada. Um teste que chamasse a função interna
diretamente exercitaria o componente, não a integração — a distinção custou
uma correção real numa etapa anterior, quando testes de MCP chamavam o handler
sem passar pelo servidor.

**E2E** — o teste invoca o grafo compilado e acompanha a execução inteira, do
ponto de entrada ao término único, incluindo o que foi gravado em disco. Não há
fronteira de protocolo envolvida; o alvo é o comportamento do sistema completo.

**Aceitação** — o teste reproduz o critério do enunciado tal como ele seria
verificado por quem avalia: entrada adversarial, ação bloqueada, mensagem
literal conferida caractere a caractere, zero chamada ao modelo, zero relatório
de diagnóstico gerado e código de saída 1.

## Como a suíte é executada

```console
$ python -m pytest -q
345 passed
```

Sem `OPENAI_API_KEY` no ambiente e com a rede externa bloqueada por
interceptação das chamadas de saída de socket — o bloqueio é confirmado por um
controle negativo que tenta uma conexão e a vê recusada. Nenhum teste depende
de serviço externo: o modelo é injetado como dependência e substituído por uma
implementação determinística.

## Como um teste é aceito

Um teste só é aceito depois de ter sido **visto falhando**. A prática vale para
todo teste novo e é medida por campanhas de mutação: cada decisão do código é
removida ou invertida, uma por vez, e a suíte precisa reprovar. Mutação que
sobrevive indica teste cego, e já apontou defeitos reais mais de uma vez —
testes que se ancoravam na própria constante que deveriam vigiar, e testes cujo
dado de entrada nunca alcançava o comportamento descrito na asserção.

## Prioridade

A ordem de importância entre cenários, e a justificativa, estão em
[`priorizacao-risco.md`](priorizacao-risco.md).

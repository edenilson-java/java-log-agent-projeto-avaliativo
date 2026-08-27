# Log da etapa de testes

Saída bruta da segunda das duas etapas do pipeline analisadas neste projeto.
É o mesmo comando que o workflow executa no passo **Testes**, rodado localmente
sobre a árvore de trabalho candidata ao versionamento.

## Como foi produzido

| Campo | Valor |
|---|---|
| Comando | `pytest -q --disable-warnings` |
| Ferramenta | pytest 9.1.1 |
| Interpretador | Python 3.12.10 |
| Ambiente | local, sem chave de modelo e sem acesso a rede externa |
| Código de saída | `0` |

## Saída bruta

```text
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 59%]
........................................................................ [ 79%]
........................................................................ [ 98%]
....                                                                     [100%]
364 passed in 5.58s
```

## O que a saída significa

Cada ponto é um teste que passou; `-q` suprime a listagem por nome e
`--disable-warnings` remove o sumário de avisos, deixando o resultado. A linha
final é o veredito: **364 testes, nenhuma falha, nenhum erro, nenhum pulado**.

Ausência de `s`, `F`, `E` ou `x` na matriz de pontos é informação: não há teste
ignorado, nem falha tolerada, nem falha esperada. Uma suíte com pulos silenciosos
mostraria `s` aqui.

## Distribuição dos 364 testes

| Arquivo | Testes | O que cobre |
|---|---:|---|
| `tests/test_security.py` | 98 | política de autonomia, três famílias de conteúdo hostil, redação de credenciais |
| `tests/test_observability.py` | 56 | os dois sinais correlacionados, redação recursiva, todas as rotas |
| `tests/test_memory.py` | 39 | isolamento por thread, limites do contexto, chave real do checkpointer |
| `tests/test_api.py` | 38 | fronteira HTTP e fronteira CLI |
| `tests/test_graph_advanced.py` | 32 | rotas, paralelização, condições de parada |
| `tests/test_resilience.py` | 25 | quatro formas de falha do modelo e o fallback |
| `tests/test_mcp.py` | 22 | fronteira MCP, atravessando `call_tool` |
| `tests/test_tools.py` | 20 | leitura e escrita confinadas, portabilidade de caminho |
| `tests/test_devops.py` | 19 | métricas da série, recusa de série não rotulada, contrato do workflow |
| `tests/test_validation.py` | 8 | validação de entrada herdada |
| `tests/test_routing.py` | 7 | roteamento herdado |
| **Total** | **364** | |

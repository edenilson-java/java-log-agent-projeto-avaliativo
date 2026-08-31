# Evolução do mini-projeto

## Princípio

Este projeto **evolui** o mini-projeto do Módulo 2, já entregue e avaliado. Não foi
construído do zero. A seção 2 do enunciado autoriza a continuidade e exige demonstrar
"quais capacidades foram mantidas, quais foram refatoradas e quais evoluções foram
adicionadas" — é o que as tabelas abaixo registram.

O ponto de partida é a fotografia do mini-projeto com **36 arquivos**. Nenhum deles foi
descartado. Artefatos locais — `.git`, `.env`, `.venv`, `.pytest_cache`, `__pycache__` e
os relatórios gerados em `output/` — não foram transportados: não são código, são
resíduo de execução.

Cada ciclo registrado neste documento aconteceu **neste projeto**, no momento em que
ocorreu, e traz a evidência real: o problema observado, a alteração, o teste ou lint
executado e o resultado obtido.

## Mantido

| Elemento original | Decisão | Evidência |
|---|---|---|
| Os nove prompts `docs/prompts/01` a `09` | Preservados integralmente, sem reescrita, renumeração ou reformatação | comparação após normalizar fim de linha: **9 de 9 idênticos** à baseline |
| `read_log_file`, `sanitize_report_name`, `write_diagnostic_report`, `extract_log_events` | Nomes e comportamento públicos preservados | `tests/test_tools.py` herdado, verde |
| `validate_log_file` e suas mensagens | Preservada, inclusive a mensagem de acesso negado | `tests/test_validation.py` herdado, verde |
| Mensagens literais de erro, acesso negado e extensão inválida | Conferidas **caractere a caractere**, com acentuação | seção [7] da validação complementar da E01 |
| `DiagnosticReport` | Campos, domínios e validador preservados | testes herdados |
| Os cinco status de saída `success`, `success_fallback`, `success_no_errors`, `invalid_output`, `error` | Preservados como estão; os novos são acréscimo | `src/state.py` |
| Regex de extração de exceções e eventos | Expressões preservadas | contagens dos três logs conferidas: 1/1, 2/1, 0/0 |
| Três logs de exemplo e três relatórios de referência | Preservados byte a byte | transporte binário conferido |
| `slides/apresentacao.pdf` e `.gitattributes` | Preservados como registro histórico | árvore do repositório |
| Suíte herdada de 26 testes | Preservada e verde após toda a refatoração | `pytest -q` → `26 passed` |

## Refatorado

| Arquivo | Motivo | Resultado real |
|---|---|---|
| `src/state.py` | Estado tipado ampliado para correlação, memória, segurança, controle de parada, paralelismo e métricas; reducers para o fan-in | os 26 testes herdados continuam verdes — a ampliação é aditiva |
| `src/schemas.py` | `StrictModel` como base, com `extra="forbid"`, endurecendo a fronteira | `DiagnosticReport` inalterado em campos e domínios |
| `.env.example` | Passou a declarar todas as variáveis de configuração, com comentário por variável e **nenhum valor real** | varredura de segredos: zero ocorrência |
| `.gitignore` | Passou a ignorar `output/*` com exceção do `.gitkeep`, além de `.ruff_cache` | `git check-ignore -v .env` → `.gitignore:2:.env` |
| `requirements.txt` | Ampliado de 6 para 12 dependências, agrupadas por finalidade | `pip check` → `No broken requirements found` |
| `src/graph.py` (E02) | Topologia ampliada: nós de controle, fan-out/fan-in, cinco rotas, término único e fachada `JavaLogGraph` | os 26 testes herdados continuam verdes **sem alteração**; 28 testes novos |
| `src/nodes.py` (E02) | Acrescentados os nós de controle e as duas branches paralelas; nós e funções herdados preservados | `classificar_log` e `extrair_eventos` mantidos e reaproveitados |
| `src/tools.py` (E03) | Contrato estruturado `read_log_as_response`, com validação de tipo na entrada; caminho em saída pública com `as_posix()` | os 4 nomes públicos herdados preservados; mensagens literais intactas |
| `src/schemas.py` (E03) | Acrescentados os cinco contratos de fronteira, todos com `extra="forbid"` e `StrictStr` | tipo errado devolve HTTP 422 |
| `src/main.py` (E03) | CLI passou a propagar `blocked` e `cancelled` com código 1 | cabeçalho e linhas literais preservados |
| `tests/test_tools.py` (E03) | Portabilidade de caminho e recusa de tipo errado | fecham pontos cegos revelados por campanha de mutação e por teste de fronteira |
| `src/graph.py` (E04) | Checkpointer ligado em `create_graph(checkpointer=...)`; `thread_id` normalizado na fachada e **com precedência sobre o `configurable` do chamador**; limpeza dos campos que pertencem a uma execução só | a segunda invocação de uma thread recupera contexto **sem** herdar o resultado da primeira; identificador público e chave real do checkpointer **coincidem** |
| `src/nodes.py` (E04) | `finalizar_execucao` grava `memory_context`; `diagnosticar` consome o contexto recuperado | o *template* do prompt herdado permanece **byte a byte** o mesmo — o contexto entra pelo texto das evidências |
| `README.md` (E04) | Seção **Contexto e memória**, rascunho da E10: estratégia, origem do contexto, o que é descartado e a justificativa de não usar RAG | 10 blocos finais consolidados na E10 |
| `src/nodes.py` (E05) | Nó `verificar_seguranca`: aplica a política e redige tudo o que deriva do arquivo lido | `log_content`, `exceptions`, `extracted_events`, `evidence`, `parallel_findings` e `memory_context` saem redigidos |
| `src/graph.py` (E05) | A governança entra entre o fan-in e a decisão de diagnóstico | o grafo passa de 15 para **16 nós**; `consolidar_analises` não alcança mais a decisão sem passar pela política |
| `src/nodes.py` (E06) | `finalizar_execucao` emite os dois sinais correlacionados; `diagnosticar` conta a tentativa e parametriza o modelo pela configuração | toda rota emite os dois sinais, inclusive erro, bloqueio, cancelamento e limite |
| `src/schemas.py` (E06) | Contrato `AuditEvent` para a linha de auditoria | recusa status fora do domínio, campo extra, latência negativa e campo faltando |
| `src/observability.py` (E07) | O campo livre do log de aplicação deixa de publicar `http_status` | o sinal passa a conter apenas o que a execução produziu |

## Adicionado

| Componente | Finalidade | Evidência |
|---|---|---|
| `src/config.py` | Configuração tipada e imutável por variável de ambiente, com a chave em `SecretStr` | **13 verificações** na validação complementar da E01, seções [4] e [5] |
| `docs/evolucao-mini-projeto.md` | Este documento | — |
| `tests/test_graph_advanced.py` (E02) | Cobertura do que a evolução acrescentou ao fluxo | 28 testes; 3 mutações deliberadas detectadas |
| `src/api.py` (E03) | API local FastAPI: `/health`, tool read-only e análise | 200/400/409/422 comprovados |
| `src/mcp_server.py` (E03) | Servidor MCP local por stdio, somente a capability `read_log` | read-only comprovado: não grava e não chama o modelo |
| `tests/test_api.py` (E03) | Integração pela fronteira HTTP e CLI | 35 testes |
| `tests/test_mcp.py` (E03) | Integração pela fronteira MCP, in-process, atravessando `call_tool` | 22 testes |
| `src/memory.py` (E04) | Checkpointer `InMemorySaver` e montagem do config de thread | **100 verificações** na validação complementar da etapa; nada de persistência em disco e nada de rede |
| `tests/test_memory.py` (E04) | Recuperação na mesma thread, isolamento entre threads, limites do contexto, recusa de `thread_id` inválido e a **chave real do checkpointer** pelo caminho do `config` | 39 testes; **16 mutações deliberadas, 16 detectadas** |
| `src/security.py` (E05) | Política de autonomia, detecção das três famílias e redaction de dez formatos de credencial | **158 verificações** na validação complementar da etapa; não importa `ChatOpenAI`, `httpx`, `socket` nem `subprocess` |
| `tests/test_security.py` (E05) | Aceitação do cenário adversarial e cobertura da governança | 98 testes; **21 mutações deliberadas, 21 detectadas** |
| `examples/logs/adversarial-prompt-injection.log` (E05) | Fixture do cenário de risco, integralmente fictícia | dispara as três famílias e **não contém segredo**, provado por `redact_sensitive_text` devolvendo o arquivo inalterado |
| `docs/seguranca/politica-autonomia.md` (E05) | O que é permitido, o que é bloqueado, o que exige humano | — |
| `docs/seguranca/cenario-adversarial.md` (E05) | Entrada, comportamento esperado, resultado obtido e evidência | execução real da CLI, código de saída 1 |
| `src/observability.py` (E06) | Dois sinais JSONL correlacionados, com redaction recursiva, escrita serializada e a causa do fallback registrada | **172 verificações** na validação complementar da etapa; não importa `ChatOpenAI`, `httpx`, `requests` nem `socket` |
| `tests/test_observability.py` (E06) | Correlação, redaction, investigação de execução real, todas as rotas e o contrato de auditoria | 56 testes |
| `tests/test_resilience.py` (E06) | Timeout configurável, tentativa única, fallback nas quatro formas e a causa registrada nos sinais | 25 testes |
| `docs/qa/diff-baseline-real.patch` (E07) | Diff real entre a baseline transportada e o estado evoluído | 19 arquivos, `+4540/-64`; `git apply --check` em código zero e reprodução idêntica numa árvore limpa |
| `docs/qa/code-review-ia.md` (E07) | Revisão assistida por IA do diff, com o achado, a correção e os resultados | quatro elementos rastreáveis: localização, problema, trecho anterior e diff da correção |
| `docs/qa/estrategia-testes.md` (E07) | Classificação da suíte em integração, E2E, aceitação e unidade | integração declarada como o tipo que cumpre o mínimo do item 4.7 |
| `docs/qa/priorizacao-risco.md` (E07) | Ordem dos cenários por custo da falha | bloqueio adversarial em primeiro, com justificativa |
| `.github/workflows/ci.yml` (E08) | Pipeline com lint, testes e compilação, sem segredo e sem passo de publicação | três runs reais no GitHub Actions, todos `success` |
| `src/devops.py` (E08) | Detecção de anomalia e estimativa de risco sobre série rotulada | os cinco valores congelados reproduzidos; a série sem rótulo é recusada em código |
| `examples/devops/pipeline_runs.json` (E08) | Série **simulada e declarada**, com `purpose` e `source` | `load_pipeline_runs` recusa carregar sem o rótulo |
| `tests/test_devops.py` (E08) | Métricas, recusas, fronteiras do crescimento e contrato do workflow | 19 testes; **7 mutações deliberadas, 7 detectadas** |
| `docs/devops/` (E08) | Logs reais de lint e testes, análise dos dois logs, anomalia justificada e logs do pipeline remoto | cinco documentos, com saídas literais e carimbos de tempo do run |
| `docs/low-code/javalog-agent-n8n.json` (E09) | Fluxo de três nós que apenas orquestra a chamada à aplicação | importado e **executado** em instância local; nenhuma credencial |
| `tests/test_n8n_workflow.py` (E09) | Estrutura do fluxo, ausência de credencial e reprodutibilidade documentada | 28 testes |
| `docs/low-code/reproducao.md` (E09) | Pré-requisitos, duas sequências de reprodução e o registro da execução real | execuções com identificador, status, código HTTP e sequência dos nós |
| `docs/low-code/decisao-integracao.md` (E09) | Escolha da ferramenta, desenho do fluxo e alternativas descartadas | seis alternativas, duas delas reprovadas pela execução real |
| `tests/test_config.py` (E10) | Configuração tipada, imutável, com a chave encapsulada e sem vazamento | 19 testes |
| `docs/arquitetura.md` (E10) | Diagrama do grafo, rotas, paralelização, parada e as três fronteiras | exigido pelo item 5.2 |
| `docs/evidencias/` (E10) | Cenários, testes, observabilidade, instalação, varreduras, pacote e fronteiras | sete documentos, com saídas reais |
| `docs/prompts/10-sistema-final.md` (E10) | Único prompt novo, acrescentado ao fim da série histórica | os nove anteriores permanecem intocados |

## Removido ou substituído

Nada foi removido. Os 36 arquivos da baseline estão presentes.

## Ciclos reais de refinamento

### Ciclo 1 — o lint reprovou o código herdado (E01)

**Problema observado.** Ao rodar `ruff check src tests` pela primeira vez, após o
transporte, o resultado foi **15 ocorrências** em sete arquivos herdados: `src/main.py`,
`src/nodes.py`, `src/tools.py`, `src/validation.py`, `tests/fake_llm.py`,
`tests/test_tools.py` e `tests/test_validation.py`.

A causa não é o código estar errado: é que o projeto **não possui configuração própria de
ruff**, e a versão fixada (`0.16.4`) habilita por padrão um conjunto de regras muito mais
amplo do que as versões antigas, que verificavam apenas `E4`, `E7`, `E9` e `F`. Regras
como `BLE001`, `ISC004`, `FURB188`, `UP045` e `PLR0402` passaram a valer.

**Alteração realizada.** Correções **exclusivamente de lint**, sem alterar comportamento
nem literais:

| Regra | Ocorrências | Correção |
|---|---|---|
| `ISC004` | 7 | concatenação implícita de strings envolvida em parênteses |
| `BLE001` | 4 | `# noqa: BLE001` com a justificativa da fronteira (CLI, LLM, I/O) |
| `FURB188` | 1 | `removesuffix` no lugar de fatiamento condicional |
| `UP045` | 1 | `Optional[X]` para `X \| None` |
| `PLR0402` | 1 | `from src import tools` no lugar do alias |
| `F401` | 1 | import não utilizado removido |

As quatro capturas amplas de exceção foram **documentadas, não eliminadas**: são
fronteiras onde o objetivo é converter qualquer falha em estado observável, e removê-las
mudaria o comportamento que os testes herdados garantem.

**Teste executado.** `ruff check src tests`, `pytest -q` e conferência dos literais.

**Resultado obtido.**

```text
ruff check src tests   ->  All checks passed!   (exit 0)
pytest -q              ->  26 passed            (exit 0)
literais herdados      ->  5 de 5 idênticos, caractere a caractere
                           (inclui as duas mensagens do prompt renderizado)
```

A reparentetização do prompt do LLM foi o ponto de maior risco, porque mexe no texto
enviado ao modelo. Por isso o prompt renderizado passou a ser **verificação permanente**
da validação complementar: as mensagens `system` e `user` são renderizadas com valores sintéticos
e comparadas **caractere a caractere** com os literais esperados. Antes disso, a
preservação do prompt era afirmada; agora é provada a cada execução.

### Ciclo 2 — a varredura de segredos acusou a si mesma (E01)

**Problema observado.** A primeira execução da varredura de recursos proibidos retornou
**4 ocorrências**, e todas eram **falsas**:

| Ocorrência | Por que era falsa |
|---|---|
| `README.md:113` | `OPENAI_API_KEY=sua_chave` é marcador didático, não credencial |
| `src/config.py:26` | `openai_api_key: SecretStr \| None = None` é anotação de tipo |
| `src/config.py:98` | `openai_api_key=SecretStr(key)` é construção de objeto |
| `.env.example` | acusado como se fosse `.env`, sendo que o enunciado **exige** esse arquivo |

Os dois defeitos eram do próprio scanner: o padrão de credencial exigia apenas 8
caracteres no valor, o que capturava identificadores de código; e a checagem de arquivo
proibido usava `startswith`, e `.env.example` começa com `.env`.

**Alteração realizada.** O valor passou a exigir **20 caracteres ou mais**, porque chave
real de provedor é longa e opaca enquanto marcador é curto e legível; foi acrescentado um
padrão por **prefixo** conhecido (`ghp_`, `gho_`, `github_pat_`), onde o tamanho não
importa; e a checagem de arquivo proibido passou a exigir **correspondência exata**,
mantendo prefixo apenas para diretórios.

**Teste executado.** Varredura completa, mais um **controle negativo**: uma isca com
segredo sintético, montado em tempo de execução, foi criada dentro de `src/` e a
varredura foi repetida.

**Resultado obtido.**

```text
varredura sobre a árvore   ->  NADA ENCONTRADO — zero ocorrências   (exit 0)
com a isca plantada        ->  OCORRENCIA chave de API estilo OpenAI -> src/_isca_temporaria.py:1   (exit 1)
após remover a isca        ->  NADA ENCONTRADO — zero ocorrências   (exit 0)
```

O controle negativo é o que dá valor ao resultado: sem ele, "zero ocorrências" seria
indistinguível de um scanner quebrado.

**Correção posterior, na revisão da própria lista de isenções.** A primeira versão do scanner mantinha uma
lista de isenções com três itens, e dois deles eram indefensáveis:

| Item isento | Por que a isenção estava errada |
|---|---|
| `.env.example` | é justamente o arquivo com **maior** chance de receber uma chave real por descuido, porque serve de molde para o `.env`. Isentá-lo removia da varredura o alvo mais provável de todos |
| `src/security.py` | é **código do produto**. Um módulo inteiro fora da varredura é um ponto cego permanente |

Ambos foram removidos das isenções. Restou **um único** item: a fixture adversarial, cujo
conteúdo é declaradamente fictício. Quando `src/security.py` existir (E05), os padrões de
detecção que ele contém serão tratados pontualmente — montados em tempo de execução, como
este próprio scanner faz —, nunca isentando o arquivo inteiro.

**Controle negativo direcionado ao `.env.example`.** Para comprovar que o arquivo passou a
ser realmente inspecionado, os bytes originais foram preservados, um segredo sintético foi
inserido nele, a varredura foi executada, e os bytes foram restaurados em bloco `finally`:

```text
bytes originais : 949  md5=38839b43fb053568d0cf900c76894642
com a isca      : OCORRENCIA chave de API estilo OpenAI -> .env.example:31
                  OCORRENCIA atribuicao de credencial   -> .env.example:31
                  exit=1
apos o finally  : 949 bytes, md5=38839b43fb053568d0cf900c76894642  (idêntico)
nova varredura  : NADA ENCONTRADO — zero ocorrências, exit=0
```

O `finally` não é detalhe de estilo: garante a restauração mesmo se a asserção falhar no
meio do teste. Um controle negativo que deixa resíduo no repositório é pior que nenhum.

### Ciclo 3 — o fan-out da forma mais óbvia executa a branch no caminho de erro (E02)

**Problema observado.** Ao modelar a paralelização, a forma mais direta seria uma aresta
condicional levando a uma branch e uma aresta incondicional levando à outra:

```python
workflow.add_conditional_edges("ler_log", route_ler_log, {"erro_leitura": "gerar_resposta_erro", "sucesso": "analisar_excecoes"})
workflow.add_edge("ler_log", "analisar_eventos")   # incondicional
```

Antes de adotá-la, ela foi **testada em um grafo mínimo isolado**. O resultado mostrou que
a aresta incondicional faz a segunda branch executar **também no caminho de erro** — ou
seja, analisando conteúdo que nunca foi lido:

```text
OPCAO 2: conditional para 'a' + add_edge incondicional para 'b'
  sucesso -> ['A', 'B']
  falha   -> achados: [{'source': 'B'}]   <- 'b' rodou mesmo no erro
```

**Alteração realizada.** A rota `route_ler_log` passou a devolver uma **lista de destinos**,
com o `path_map` declarado como lista de nós possíveis:

```python
def route_ler_log(state) -> list[str]:
    if state.get("error"):
        return ["gerar_resposta_erro"]
    return ["analisar_excecoes", "analisar_eventos"]
```

Uma terceira forma — `path_map` com lista como valor — foi testada e **não é suportada**:
o LangGraph tenta usar o valor como chave e levanta `TypeError: unhashable type: 'list'`.

**Teste executado.** Grafo mínimo isolado para as três formas; depois
`test_branches_nao_executam_no_erro_de_leitura` e a checagem automatizada da etapa; e uma **mutação
deliberada** revertendo o fan-out para a forma descartada.

**Resultado obtido.**

```text
forma adotada, caminho de erro  ->  achados: []  (nenhuma branch executou)
mutação de volta à forma antiga ->  1 failed, 8 passed   (o teste detecta)
suíte completa                  ->  54 passed
```

### Ciclo 4 — a verificação de transporte acusava falsa divergência (E02)

**Problema observado.** Ao rodar a checagem de transporte da E01 como teste de regressão
dentro da E02, ela acusou cinco arquivos supostamente corrompidos, entre eles o prompt
histórico `01` e os três logs de exemplo — justamente os arquivos que **não podem** mudar.

**Diagnóstico.** O conteúdo **versionado** estava intacto. O `git show HEAD:` do prompt `01`
devolve `CRLF=0` e `776 bytes`, idêntico à baseline. O que diverge é a **árvore de
trabalho**: no Windows o Git converte LF para CRLF no checkout.

| Arquivo | Baseline | Árvore de trabalho | Bruto igual? | Normalizado igual? |
|---|---|---|---|---|
| `docs/prompts/01-...md` | 21 LF, 776 bytes | 21 CRLF, 797 bytes | não | **sim** |
| `examples/logs/null-pointer-exception.log` | 6 LF, 490 bytes | 6 CRLF, 496 bytes | não | **sim** |

O defeito era da própria checagem: a seção de transporte comparava **bytes brutos**, enquanto
o critério do projeto exige comparação **após normalizar fim de linha**. A seção dos prompts já
normalizava corretamente; a de transporte, não.

**Alteração realizada.** A comparação de transporte passou a normalizar fim de linha, e foi
declarado o conjunto `REFATORADOS_E02` com os arquivos que a E02 legitimamente alterou, para
que a checagem siga falhando se qualquer outro arquivo divergir sem declaração.

**Teste executado.** A checagem de transporte da E01 reexecutada como regressão dentro da E02.

**Resultado obtido.**

```text
antes da correção  ->  2 FALHA(S): 5 arquivos "divergentes inesperados"
após a correção    ->  TODAS AS VERIFICACOES DA E01 PASSARAM  (38 checagens, exit 0)
```

Este ciclo confirma, na prática, duas decisões tomadas antes: escrever os arquivos em modo
binário no transporte, e a exigência de que a comparação dos nove prompts seja
sempre feita após normalização.

### Ciclo 5 — erro de fronteira no limite de passos (E02)

**Problema observado.** A reprodução do defeito na rota de limite mostrou que

```text
route_inicializar({"current_step": 32, "max_steps": 32})
  obtido:   "continuar"
  esperado: "limite"
```

A condição implementada era `current_step > max_steps`, quando a tarefa T031 exige
`current_step >= max_steps`. Com `>`, o passo de número `max_steps` ainda executava e o
limite valia na prática como `max_steps + 1` — um erro clássico de fronteira.

**Por que a suíte não pegou.** Os testes cobriam apenas valor **acima** do limite
(`current_step=33, max_steps=32` e `current_step=50, max_steps=10`). Nenhum exercitava a
**igualdade**, que é justamente onde os dois operadores divergem. O teste passava, e passava
por acidente: teria passado igual com o operador errado — que foi o que aconteceu.

**Alteração realizada.**

| Onde | Mudança |
|---|---|
| `src/graph.py` | condição de `>` para `>=`, com comentário explicando por que a igualdade encerra |
| `tests/test_graph_advanced.py` | `test_route_inicializar_limite_na_igualdade` (32/32 → limite) e `test_route_inicializar_continua_um_passo_antes_do_limite` (31/32 → continuar) |
| `tests/test_graph_advanced.py` | `test_limite_de_passos_encerra_exatamente_na_fronteira`: entrada com `current_step=9` e `max_steps=10`; após o incremento de `inicializar_execucao` o passo vira 10 e a execução tem de encerrar ali, sem validar, ler, escrever **nem chamar o modelo** |
| `tests/test_graph_advanced.py` | `test_um_passo_antes_do_limite_a_execucao_prossegue`: o outro lado da fronteira segue normalmente |
| validação complementar da etapa | verificação da igualdade na rota isolada **e** no fluxo completo |

Para provar que o modelo não é acionado, foi criada uma subclasse local `ContandoLLM` com
contador de chamadas, em vez de alterar o `fake_llm.py` herdado.

**Teste executado.** Suíte completa, validação complementar, e uma **mutação deliberada**
revertendo o operador para `>`.

**Resultado obtido.**

```text
fronteira, os dois lados:
  step=31 max=32 -> continuar     step=32 max=32 -> limite
  step=9  max=10 -> continuar     step=10 max=10 -> limite

pytest -q            ->  58 passed
validacao complementar ->  62 checagens, 0 falhas, exit 0

com o operador revertido para '>':
  validacao complementar ->  exit 1  — FALHOU route_inicializar: limite NA IGUALDADE
  pytest             ->  2 failed, 30 passed
```

A lição registrada é sobre o método, não sobre o operador: **teste de limite que só exercita
valor acima do limite não testa o limite**. A fronteira precisa ser exercitada dos dois
lados — no valor exato e no imediatamente anterior.

### Ciclo 6 — o SDK do MCP não tem o módulo mais citado (E03)

**Problema observado.** A forma mais divulgada de criar um servidor MCP em Python é
`from mcp.server.fastmcp import FastMCP`. No SDK instalado (`mcp==2.0.0`) esse módulo
**não existe**.

**Como foi tratado.** Em vez de escrever o import e descobrir o erro em tempo de execução,
o pacote instalado foi inspecionado **antes** de qualquer linha de código:

```text
submodulos de mcp.server: ... lowlevel, mcpserver, models, runner, session, sse, stdio ...
  --  mcp.server.fastmcp: ModuleNotFoundError
  OK  mcp.server.mcpserver -> ['AESGCMRequestStateCodec', ...]
```

A assinatura real de `MCPServer.__init__`, do decorador `.tool()` e de `.run()` foi lida por
`inspect.signature` antes do uso.

**Alteração realizada.** `src/mcp_server.py` usa `mcp.server.mcpserver.MCPServer`, com
`.tool(name=..., title=..., description=..., structured_output=True)` e `.run("stdio")`.

**Teste executado.** `tests/test_mcp.py`, in-process, mais a checagem automatizada da etapa.

**Resultado obtido.** `MCP tools: ['read_log']`; 15 testes de MCP verdes; nenhum resource e
nenhum prompt expostos.

A lição: **API de biblioteca se confere no pacote instalado, não na memória**. Custou uma
inspeção de dois minutos e evitou um erro que só apareceria em execução.

### Ciclo 7 — lint pegou um import adiantado desnecessário (E03)

**Problema observado.** `read_log_as_response` foi escrita com o import de `ReadLogResponse`
dentro da função e a anotação de retorno entre aspas, por receio de import circular. O ruff
reprovou:

```text
F821 Undefined name `ReadLogResponse`
  --> src\tools.py:203:46
```

**Diagnóstico.** Não havia ciclo algum: `schemas.py` importa `state.py` e nada mais;
`tools.py` importar `schemas.py` não fecha ciclo. O import adiantado era precaução infundada
que criou um defeito real — a anotação ficou irresolvível.

**Alteração realizada.** Import movido para o topo do módulo e anotação de retorno direta.

**Resultado obtido.** `ruff check src tests` → `All checks passed!`; suíte → `100 passed`.

### Ciclo 8 — a suíte versionada tinha ponto cego revelado por mutação (E03)

**Problema observado.** A campanha de mutação da E03 revelou algo mais grave que uma regra de
lint. Das três mutações aplicadas, **duas passaram sem que a suíte versionada as
detectasse**:

| Mutação | Suíte versionada |
|---|---|
| `cancelled` deixa de mapear para 409 | **detectou** |
| `as_posix()` revertido para `str(path)` | **cega** |
| CLI para de propagar `blocked`/`cancelled` | **cega** |

Ou seja: quem clonasse o repositório e rodasse `pytest` teria a suíte verde com duas
regressões reais presentes.

**Alteração realizada.** Quatro testes acrescentados à suíte **versionada**:

- `tests/test_tools.py`: portabilidade do caminho devolvido por
  `write_diagnostic_report` e por `read_log_as_response`;
- `tests/test_api.py`, seção *Fronteira CLI*: código de saída para os seis desfechos
  possíveis e preservação das linhas literais da CLI.

Os testes de CLI ficaram em `test_api.py` porque a árvore entregável prevista
**não contempla** um `test_cli.py`, e acrescentar um 81º arquivo mudaria a estrutura acordada.

**Teste executado.** As três mutações foram reaplicadas, agora rodando **somente** a suíte
versionada.

**Resultado obtido.**

```text
as_posix() revertido em write_diagnostic_report  ->  1 failed, 108 passed
CLI para de propagar blocked/cancelled           ->  2 failed, 107 passed
as_posix() revertido no contrato estruturado     ->  1 failed, 108 passed
```

A lição é sobre onde a garantia mora: **só protege o repositório aquilo que está versionado
junto com ele**. Checagem auxiliar é ferramenta de desenvolvimento; o que defende o
repositório é a suíte versionada.

### Ciclo 9 — um rótulo de classificação ficou factualmente falso (E03)

**Problema observado.** A checagem de transporte da E01 classificava `src/tools.py`, `src/main.py` e
`tests/test_tools.py` como **"corrigidos só por lint"**. Depois que a E03 fez mudanças
**funcionais** nesses mesmos arquivos, o rótulo passou a afirmar algo falso — e a checagem
continuava passando, porque olhava só o conjunto, não o motivo.

**Alteração realizada.** Criado o conjunto `REFATORADOS_E03`, com nota explícita de que um
arquivo pode aparecer em mais de um conjunto: correção de lint na E01 e mudança funcional na
E03 são coisas diferentes sobre o mesmo arquivo.

**Resultado obtido.** O relatório passou a distinguir as quatro categorias, e segue
falhando se qualquer arquivo divergir sem declaração:

```text
..  corrigidos so por lint : ['src/main.py', 'src/nodes.py', 'src/tools.py', ...]
..  refatorados na E02     : ['src/graph.py', 'src/nodes.py']
..  refatorados na E03     : ['src/main.py', 'src/schemas.py', 'src/tools.py', 'tests/test_tools.py']
```

Uma checagem que passa com rótulo errado é pior que uma que falha: ela documenta uma
inverdade e ninguém percebe.

### Ciclo 10 — três lacunas de fronteira nos contratos externos (E03)

**Problema observado.** Três lacunas objetivas nos contratos de fronteira da E03,
todas reproduzidas antes de qualquer correção.

**1. A função interna quebrava com tipo errado.**

```text
read_log_as_response(123)   -> TypeError: argument should be a str or an os.PathLike...
read_log_as_response(None)  -> status=error   (funcionava por acidente)
read_log_as_response(["x"]) -> TypeError
```

V030 exige erro **estruturado** para entrada inválida, tipo errado e vazia. O `None` passava
apenas porque `if file_path else ""` o tratava como falso — coincidência, não validação.
A função interna é chamada por caminhos que **não** passam por schema Pydantic: a tool MCP e
qualquer chamador direto.

**2. Os testes de MCP não atravessavam o servidor.** Chamavam `read_log_tool` diretamente,
o que exercita o handler mas não o **registro** nem a **execução** pelo `MCPServer`.
Apresentar isso como teste de integração MCP seria impreciso.

**3. O teste de `blocked` só consultava o dicionário.** Verificava
`HTTP_POR_STATUS["blocked"] == 409` sem nunca chamar o endpoint. O mapa poderia estar certo e
o endpoint errado, e o teste continuaria verde.

**Alteração realizada.**

| Lacuna | Correção |
|---|---|
| 1 | `read_log_as_response` valida `isinstance(file_path, str)` **antes** de `Path` ou `read_log_file`, devolvendo o contrato de erro completo. 8 testes versionados parametrizados |
| 2 | 7 testes novos em `tests/test_mcp.py` atravessando `server.call_tool("read_log", ...)`, com a corrotina resolvida no teste |
| 3 | `test_analyze_bloqueado_devolve_409_no_endpoint`: grafo substituído por um duplo que devolve estado terminal `blocked`, e o endpoint chamado pelo `TestClient` |

Os endpoints HTTP continuam devolvendo **422** para tipo errado, porque o schema valida antes
da função interna — comprovado para `123`, `None`, lista e dicionário.

**O que a integração real revelou sobre o SDK.** Atravessar `call_tool` mostrou o contrato
verdadeiro da fronteira MCP, que a chamada direta escondia:

| Situação | Resultado no protocolo |
|---|---|
| caminho feliz | `is_error=False`, `structured_content` com o contrato |
| erro de domínio (path traversal) | `is_error=False` — erro de **domínio** vem estruturado, não como erro de protocolo |
| tipo errado no payload | `ToolError` levantado pelo SDK **antes** do handler |
| capability inexistente | `ToolError: Unknown tool` |

**Teste executado.** Suíte completa, validação complementar reescrita para usar `call_tool`, e
três mutações deliberadas — uma por lacuna.

**Resultado obtido.**

```text
pytest -q      ->  124 passed
validacao complementar ->  97 checagens, 0 falhas, exit 0

mutacoes, contra a suite VERSIONADA:
  remove a validacao de tipo          ->  7 failed, 117 passed
  blocked deixa de mapear para 409    ->  2 failed, 122 passed
  MCP expoe capability de escrita     ->  2 failed, 122 passed
```

A lição repete a do Ciclo 8, num nível acima: **testar o handler não é testar a integração**.
As três lacunas tinham a mesma raiz — verificar o componente isolado e chamar isso de
fronteira. A fronteira só está testada quando o teste passa por ela.

### Ciclo 11 — o teste do limite comparava com a própria constante (E04)

**Problema observado.** A campanha de mutação da E04 aplicou 14 mutações; 13 morreram e
**uma sobreviveu**. A mutação era trivial — subir `MEMORY_MAX_EVIDENCIAS` de `2` para `4` —
e o teste que deveria pegá-la afirmava:

```python
assert len(contexto["evidence"]) == MEMORY_MAX_EVIDENCIAS
```

A mutação move os **dois lados** da igualdade ao mesmo tempo. O teste continuava verde com
o limite dobrado, isto é, com o dobro de conteúdo atravessando a memória entre execuções —
exatamente o que o critério do enunciado cobra que seja limitado.

**Alteração realizada.** O número do contrato passou a estar escrito no teste, e não
apenas referenciado:

- `assert len(contexto["evidence"]) == 2`, com verificação de **qual** evidência sobreviveu
  (a primeira e a segunda, nessa ordem);
- teste dedicado `test_o_limite_de_evidencias_previsto_e_dois`, que fixa
  `MEMORY_MAX_EVIDENCIAS == 2` e explica por que o número está ali.

**Teste executado.** A mutação M06 foi reaplicada, e depois a campanha inteira.

**Resultado obtido.**

```text
antes  ->  M06 SOBREVIVEU          (158 passed, mutacao invisivel)
depois ->  M06 morta               (2 testes falham)
campanha final -> 15 mutacoes, 15 mortas
```

A lição é sobre onde a asserção se ancora: **um teste que se apoia na constante que deveria
vigiar não vigia nada**. Para vigiar um número, é preciso escrever o número.

### Ciclo 12 — o lint discordou da exceção escolhida, e tinha razão (E04)

**Problema observado.** `normalize_thread_id` levantava `ValueError` para os dois casos de
recusa — string vazia e tipo não-string —, por uma simetria que parecia elegante: "para
quem chama, o identificador não serve, nos dois casos". O `ruff` reprovou:

```text
TRY004 Prefer `TypeError` exception for invalid type
  --> src\memory.py:46:9
```

Exit 1, e V048 exige código 0.

**Alteração realizada.** A saída fácil seria um `# noqa: TRY004`. Em vez disso a distinção
foi acolhida, porque ela é real e útil a quem chama: string vazia é um **valor** inaceitável
que chegou da fronteira (`ValueError`); tipo não-string é um **defeito de programação** de
quem chamou (`TypeError`). O teste e o *docstring* foram atualizados junto — o texto que
justificava a simetria teria virado documentação falsa.

**Teste executado.** `ruff check .`, a suíte completa e **duas** mutações: remover a
validação de tipo, e reverter a exceção para `ValueError` com `noqa`.

**Resultado obtido.**

```text
ruff check .                              ->  All checks passed!  (exit 0)
pytest -q, sem rede e sem chave           ->  158 passed
mutacao: remove a validacao de tipo       ->  1 failed
mutacao: tipo errado volta a ValueError   ->  1 failed
```

O aviso do lint não era estilo: era um contrato de exceção mal desenhado, e suprimi-lo
teria congelado o erro.

### Ciclo 13 — o identificador público e a chave real da memória divergiam (E04)

**Problema observado.** A fachada normalizava o
`thread_id` e o gravava no estado, mas montava o `config` do LangGraph assim:

```python
runtime_config["configurable"] = {
    "thread_id": thread_id,     # o normalizado
    **configurable,             # ... e o cru do chamador sobrescrevia
}
```

Como `configurable` era expandido **depois**, o valor cru vencia. O estado dizia uma coisa
e o checkpointer gravava sob outra:

```text
config recebido ................: {'configurable': {'thread_id': '  sessao-1  '}}
thread_id gravado no estado .....: 'sessao-1'
thread_id enviado ao checkpointer: '  sessao-1  '
```

Duas consequências, ambas reproduzidas antes de qualquer correção: a mesma thread lógica se
partia em **dois checkpoints** — `sessao-1` e `  sessao-1  ` deixavam de se enxergar —, e
com estado e `config` divergentes o identificador público (`do-estado`) e a chave de
persistência (`do-config`) apontavam para lugares diferentes.

**Por que a suíte não pegou.** Os 34 testes da E04 informavam o `thread_id` **sempre pelo
estado**. O caminho pelo `config` — que é justamente o que o LangGraph usa para indexar o
checkpoint — não era exercitado por nenhum deles. O ponto cego não estava na profundidade
dos testes, e sim na **porta de entrada** que nenhum deles usava.

**Alteração realizada.**

- `src/graph.py`: o `thread_id` já escolhido e normalizado passou a vir **por último** na
  composição, `{**configurable, "thread_id": thread_id}`, preservando os demais campos que
  o chamador tenha posto em `configurable`;
- `tests/test_memory.py`: **5 testes novos** que observam o `config` **realmente entregue**
  ao grafo compilado, e não o que a fachada devolve — mais a prova de persistência por
  `get_state`, que mostra o checkpoint sob a chave normalizada e **nada** sob a crua;
- validação complementar: seção nova, com 17 verificações sobre a chave
  real, incluindo a leitura na fonte de que o `thread_id` vem por último na composição.

**Teste executado.** O defeito foi **reintroduzido** e medido separadamente contra a suíte
versionada e contra a validação complementar.

**Resultado obtido.**

```text
corrigido            ->  pytest 163 passed  |  complementar exit 0, 100 verificacoes
defeito reintroduzido->  pytest 4 failed    |  complementar exit 1, 11 verificacoes falham
```

A lição não é sobre precedência de dicionário. É sobre **por onde o teste entra**: uma
unidade pode estar coberta por dezenas de testes e ainda assim ter uma porta que nenhum
deles abre. O `thread_id` tinha duas — estado e `config` — e só uma estava sendo usada.

### Ciclo 14 — a redação cobria o prompt, mas não a resposta (E05)

**Problema observado.** A primeira versão de `verificar_seguranca` redigia apenas `evidence`,
que é o campo que alimenta o prompt. O teste escrito para o requisito falhou logo na primeira
execução, e o motivo estava na própria mensagem de erro:

```text
assert 'ghp_BBBB…' not in "{'file_path'… 'log_content': '… invalid credential ghp_BBBB…',
  'exceptions': ['java.lang.SecurityException: invalid credential ghp_BBBB…'],
  'evidence': ['java.lang.SecurityException: invalid credential [REDACTED]'] …}"
```

`evidence` estava limpo; `log_content`, `exceptions` e `extracted_events` carregavam o segredo
bruto. E o estado final não é um detalhe interno: é a **resposta pública** devolvida pela
fachada do grafo, pela API e pela CLI. Redigir só o que ia ao modelo tirava o segredo da
entrada e o devolvia pela porta de saída.

**Alteração realizada.** A redação passou a alcançar tudo o que deriva do arquivo lido —
`evidence`, `exceptions`, `extracted_events`, `parallel_findings` — mais o `log_content`, que
atravessa `sanitize_untrusted_content`, e o `memory_context` recuperado da execução anterior
da thread.

**Teste executado.** Os dois testes de vazamento — segredo vindo do arquivo e segredo vindo do
histórico da thread — verificando prompt, resposta, relatório gravado em disco e cada campo do
estado, um a um.

**Resultado obtido.**

```text
antes  ->  2 failed  (segredo presente em log_content, exceptions, extracted_events)
depois ->  228 passed
mutacao: no de seguranca para de redigir os campos derivados  ->  1 failed
mutacao: no de seguranca para de sanear o conteudo do log     ->  1 failed
mutacao: no de seguranca para de sanear a memoria recuperada  ->  1 failed
```

A lição é sobre o alcance do controle: **sanitizar a entrada do modelo não é sanitizar a
saída do sistema**. O estado é resposta pública, e todo campo dele precisa ser tratado como
tal.

### Ciclo 15 — a varredura de segredos tinha um ponto cego declarado (E05)

**Problema observado.** A fixture adversarial estava na lista `ISENTOS` da varredura de
segredos, desde a E01, sob a justificativa de conter "conteúdo declaradamente fictício". O
controle negativo executado nesta etapa mostrou o custo dessa isenção. Um segredo sintético foi
plantado, um de cada vez, em três arquivos, e a varredura foi rodada:

```text
src/security.py                                contaminado -> exit=1  acusou=True
examples/logs/adversarial-prompt-injection.log contaminado -> exit=0  acusou=False   <-- ponto cego
tests/test_security.py                         contaminado -> exit=1  acusou=True
```

Ou seja: o arquivo cujo **propósito** é conter texto hostil — e portanto aquele em que uma
credencial real passaria mais facilmente por "parte do cenário" — era exatamente o que a
varredura não olhava.

**Alteração realizada.** A isenção foi removida e `ISENTOS` ficou **vazio**. Isso só foi
possível porque a fixture foi escrita para demonstrar o ataque **sem carregar credencial
alguma**: ela pede a chave, não a exibe. O mesmo vale para `src/security.py` e
`tests/test_security.py`, cujos literais parecidos com credencial são montados em tempo de
execução, por concatenação — a solução fica no arquivo inspecionado, nunca em tirá-lo da
inspeção.

**Teste executado.** O mesmo controle negativo, com os três alvos, depois da remoção.

**Resultado obtido.**

```text
os tres alvos contaminados -> exit=1, acusou=True nos tres
estado limpo               -> exit=0, zero ocorrencias
ISENTOS                    -> conjunto vazio
```

A lição: **uma isenção é um ponto cego com nome bonito**. Enquanto ela existir, a varredura
responde "nada encontrado" sobre um arquivo que não leu.

### Ciclo 16 — um teste de limite que nunca chegava ao limite (E05)

**Problema observado.** Das 16 mutações da E05, quinze morreram e **uma sobreviveu**: remover
o teto de `sanitize_untrusted_content` não fazia teste algum falhar. O teste parecia correto:

```python
conteudo = segredo_provedor() + ("x" * (LIMITE_CONTEUDO_NAO_CONFIAVEL * 2))
saida = sanitize_untrusted_content(conteudo)
assert len(saida) <= LIMITE_CONTEUDO_NAO_CONFIAVEL
```

O padrão de redação é **guloso sobre caracteres alfanuméricos**, e o preenchimento estava
colado ao segredo. A substituição engolia os dois de uma vez:

```text
len entrada: 8035   len saida: 10   teto: 4000
```

A saída cabia no teto por já ter virado `[REDACTED]`. O corte nunca era exercitado, e a
asserção passava sem testar coisa alguma.

**Alteração realizada.** O preenchimento passou a ser separado do segredo por quebra de linha,
o que interrompe a correspondência gulosa; a asserção passou de `<=` para **igualdade exata**
com o teto, de modo que só passa se o corte tiver de fato acontecido; e um controle negativo
foi acrescentado, provando que conteúdo abaixo do teto atravessa inteiro.

**Teste executado.** A mutação S07 reaplicada, e depois a campanha inteira.

**Resultado obtido.**

```text
antes  ->  S07 SOBREVIVEU  (228 passed, mutacao invisivel)
depois ->  S07 morta       (1 teste falha)
campanha, naquele momento -> 16 mutacoes, 16 mortas
```

É a mesma lição do Ciclo 11, por outro caminho: ali o teste se ancorava na constante que
deveria vigiar; aqui o dado de entrada nunca alcançava o comportamento que a asserção
descrevia. Em ambos os casos, o teste passava — e não protegia nada.

### Ciclo 17 — a redação cobria um formato de cada família, não todos (E05)

**Problema observado.** A redação reconhecia
`sk-`, `ghp_` e `Bearer` — e apenas esses. A reprodução, por formato, mediu tanto a detecção
quanto o vazamento no estado devolvido:

```text
formato                   contains  redigiu   vaza no estado
sk- simples                   True     True             False
sk-proj- composto            False    False              True   <--
sk-svcacct- composto         False    False              True   <--
sk_ com underscore           False    False              True   <--
ghp_ classico                 True     True             False
github_pat_ fino             False    False              True   <--
Bearer maiusculo              True     True             False
bearer minusculo             False    False              True   <--
BEARER caixa alta            False    False              True   <--
```

Seis dos nove formatos atravessavam inteiros — apareciam no prompt, no `log_content`, nas
`evidence` e na resposta pública. Três causas distintas:

1. o corpo do token era lido como um bloco alfanumérico único, então `sk-proj-…` parava no
   primeiro hífen e `proj` não alcançava o comprimento mínimo;
2. `github_pat_` não constava da lista de prefixos de provedor;
3. o esquema portador era casado com sensibilidade a maiúsculas.

**Alteração realizada.**

- o prefixo passou a aceitar **componentes separados** por hífen ou underscore, consumindo o
  token inteiro — um casamento parcial deixaria o sufixo exposto, e meia credencial num log
  ainda é credencial vazada;
- `github_pat_` entrou na lista de prefixos;
- o esquema portador passou a ser reconhecido em **qualquer capitalização**;
- foi acrescentada uma **guarda de início**, `(?<![A-Za-z0-9_])`, sem a qual identificadores
  legítimos do domínio — `disk_utilizationPercentageValue…`, `task_executorThreadPool…`,
  `risk_scoreCalculated…` — passariam a ser redigidos como se fossem credencial;
- o scanner de segredos recebeu os mesmos formatos, continuando a montar os
  padrões em tempo de execução.

**Teste executado.** Dez formatos parametrizados na suíte versionada, cada um exigindo
detecção, substituição, ausência do valor completo e ausência do **fragmento final** — mais
o mesmo conjunto atravessando o fluxo real, com verificação campo a campo. Controle negativo
da varredura ampliado para **três arquivos × oito formatos**. E cinco mutações novas, uma por
decisão tomada.

**Resultado obtido.**

```text
depois da correcao: os 9 formatos -> contains=True, redigiu=True, vaza=False
suite versionada  -> 261 passed  (228 -> 261)
validacao complementar -> 158 verificacoes, exit 0
controle negativo da varredura -> 3 arquivos x 8 formatos, 24 acusacoes, 24 restauracoes
campanha de mutacao -> 21 mutacoes, 21 mortas
```

Durante a mesma rodada, uma segunda coisa apareceu: a mutação que removia a guarda de início
**sobreviveu**, porque os textos de controle escolhidos não a exercitavam — `risk_score=0.87`
não casa nem com a guarda nem sem ela, já que o valor após o separador é curto demais. Os
casos foram trocados por identificadores longos, que discriminam de fato, e a mutação passou
a morrer.

A lição: **cobrir uma família de formato não é cobrir a família**. Um único exemplar por
padrão dá a sensação de cobertura e esconde as variações — e são justamente as variações que
os provedores introduzem com o tempo.

### Ciclo 18 — a lista de campos protegidos era vigiada por ela mesma (E06)

**Problema observado.** A campanha de mutação da E06 aplicou 21 mutações; 20 morreram e **uma
sobreviveu**: esvaziar `CAMPOS_NAO_REGISTRAVEIS`, o conjunto de chaves cujo valor nunca vai
para arquivo — `log_content`, `api_key`, `senha`, `token` e outras seis. Com o conjunto
esvaziado, um payload contendo qualquer dessas chaves passaria a ser gravado nos dois sinais.

O teste que deveria pegar isso parametrizava sobre o próprio conjunto:

```python
@pytest.mark.parametrize("chave", sorted(CAMPOS_NAO_REGISTRAVEIS))
def test_scrub_substitui_campo_de_nome_sensivel(chave):
    ...
```

Esvaziar o conjunto não fazia o teste falhar — fazia a parametrização encolher. O teste
continuava verde exercitando exatamente as chaves que ainda restassem, que no limite eram
nenhuma.

**Alteração realizada.** Os dez nomes passaram a estar **escritos no arquivo de teste**, numa
lista própria, e um teste novo compara as duas listas. A parametrização usa a lista escrita,
não a constante vigiada.

**Teste executado.** A mutação foi reaplicada, e depois a campanha inteira.

**Resultado obtido.**

```text
antes  ->  esvaziar CAMPOS_NAO_REGISTRAVEIS: SOBREVIVEU (328 passed)
depois ->  morta: 2 testes falham
campanha final -> 21 mutacoes, 21 mortas
suite          -> 329 passed
```

É a terceira vez que a mesma armadilha aparece — no Ciclo 11 era um limite numérico, no Ciclo
16 um dado de entrada que não alcançava o comportamento, aqui um conjunto de nomes. A forma é
sempre a mesma: **o teste toma como referência aquilo que deveria estar verificando**, e por
isso acompanha a mudança em vez de recusá-la.

### Ciclo 19 — os sinais diziam que houve fallback, mas não por quê (E06)

**Problema observado.** Nas quatro formas de falha
do modelo, os dois sinais registravam `decision = diagnosed_by_fallback` e
`error = null`:

```text
forma                  status             error publico  error nos sinais
ausencia de chave      success_fallback   ''             None   <-- causa perdida
timeout                success_fallback   ''             None   <-- causa perdida
excecao                success_fallback   ''             None   <-- causa perdida
saida invalida         success_fallback   ''             None   <-- causa perdida
```

A raiz é uma colisão entre dois contratos legítimos. O nó `tratar_saida_invalida` zera
`state["error"]` porque o fallback é um desfecho de **sucesso** — contrato herdado da
baseline, e correto. Mas a observabilidade lia exclusivamente esse campo. O resultado é que
os sinais sabiam **que** houve fallback e não **por quê**: uma investigação não conseguiria
distinguir ausência de chave de timeout, de exceção ou de saída fora do schema.

**Alteração realizada.** Um campo interno, e não uma mudança no contrato público:

- `src/state.py`: campo `fallback_reason`, declarado como interno — a resposta pública do
  fallback continua com `error == ""`;
- `src/graph.py`: `fallback_reason` entra na limpeza dos campos de uma execução só, para que
  a causa de uma execução não reapareça na seguinte da mesma thread;
- `src/nodes.py`: `tratar_saida_invalida` captura a causa **antes** de zerar `error`, e usa
  uma causa determinística quando a etapa anterior não reportou nenhuma;
- `src/observability.py`: o campo `error` dos dois sinais passa a receber o erro final, ou a
  causa do fallback, ou `None` quando de fato não houve erro. A causa atravessa a redaction
  existente e recebe teto — mensagem de integração externa pode trazer o payload inteiro, e
  uma linha de sinal não é lugar para ele.

**Teste executado.** Treze testes versionados novos, cruzando resiliência e observabilidade
nas quatro formas, mais controles negativos: sucesso e log limpo com `error` nulo, a causa não
vazando para a execução seguinte da thread, a causa redigida quando traz credencial, e o teto
aplicado. E três mutações medidas separadamente contra a suíte versionada e contra a
validação complementar.

**Resultado obtido.**

```text
depois da correcao     -> as 4 causas presentes, distintas e identificando a forma
suite versionada       -> 342 passed  (329 -> 342)
validacao complementar -> 172 verificacoes, exit 0

mutacao: sinal volta a ler so o error publico  -> 7 failed  | checagem: 13 falhas
mutacao: fallback deixa de preservar a causa   -> 10 failed | checagem: 13 falhas
mutacao: causa sem redaction e sem teto        -> 1 failed  | checagem: 1 falha
```

A lição é sobre onde um contrato termina: **zerar um campo para preservar a semântica pública
não pode apagar a informação técnica que outro consumidor precisa**. O `error` vazio é
correto para quem lê a resposta; era errado para quem lê o sinal.

### Ciclo 20 — o log de aplicação publicava um código HTTP que nunca foi medido (E07)

**Problema observado.** A revisão do diff real entre a baseline transportada e o estado
evoluído foi conduzida por uma pergunta simples: *algum campo é publicado sem ter sido
medido?* A busca por produtores de `http_status` devolveu uma única ocorrência — a própria
inicialização com zero:

```text
src/graph.py:64          "http_status": 0,      <- inicializacao
src/observability.py:46  "http_status",         <- publicacao no sinal
src/state.py:102         http_status: int       <- declaracao
```

Declarado, zerado, publicado — e **nunca escrito**. O motivo é estrutural: o código HTTP é
decidido na fronteira, a partir do `status` do domínio, **depois** que o grafo retorna; o
sinal é emitido **dentro** do grafo, no ponto único de término. Quando a linha é gravada, o
código ainda não existe.

Medido pela fronteira HTTP:

```text
entrada                                  HTTP real   no sinal
examples/logs/application-clean.log            200          0   <-- diverge
examples/logs/adversarial-prompt-injection     409          0   <-- diverge
```

Zero não é código HTTP. Quem investigasse uma execução leria um valor que contradiz a
resposta efetivamente devolvida — e a trilha de investigação é justamente o artefato
consultado quando algo dá errado.

**Alteração realizada.** `http_status` saiu da tupla de campos publicados no campo livre.
O campo permanece no estado, disponível para a fronteira que quiser usá-lo; o que foi
retirado é a **afirmação** que não podia ser sustentada.

Três alternativas foram descartadas, e por quê: preencher o campo no grafo acoplaria o
núcleo ao protocolo HTTP, que a CLI e o servidor MCP não têm; emitir um segundo par de
sinais na fronteira quebraria o invariante de uma linha por execução em cada sinal, que é o
que torna a correlação legível; e remover o campo do estado alteraria um contrato já
estabelecido.

**Teste executado.** Um teste de **integração** em `tests/test_api.py`, parametrizado nos
dois desfechos que produzem códigos diferentes — `200` no log limpo e `409` no cenário
bloqueado. Ele entra pela porta HTTP, confere o código devolvido e depois lê a linha
gravada no sinal.

**Resultado obtido.**

```text
antes  ->  2 failed
           AssertionError: assert 'http_status' not in {'category': 'Unknown',
             'current_step': 1, 'http_status': 0, 'llm_attempts': 0, ...}
depois ->  3 passed

reproducao pela fronteira: 200 -> <ausente> | 409 -> <ausente>
suite versionada       -> 345 passed  (342 -> 345)
validacao complementar -> 69 verificacoes, exit 0
```

A lição é sobre o custo de um campo vazio numa saída observável: **omitir é honesto, zerar
é falso**. Um campo ausente faz quem lê procurar a informação em outro lugar; um campo com
valor fixo faz quem lê acreditar que já a encontrou.

### Ciclo 21 — a série malformada era recusada na categoria errada de erro (E08)

**Problema observado.** O lint reprovou `src/devops.py` na primeira execução:

```text
TRY004 Prefer `TypeError` exception for invalid type
  --> src\devops.py:45:9
```

`load_pipeline_runs` levantava `ValueError` para **todas** as recusas, inclusive
para o caso em que o arquivo não traz sequer o objeto da série — uma lista, um
número ou uma string solta no lugar do envelope.

**Diagnóstico.** As recusas não são todas da mesma natureza. Série sem o rótulo
`simulated`, série vazia, série sem uma das fases: a **forma** está certa e o
**conteúdo** está errado — isso é `ValueError`. Arquivo que não contém o objeto
da série: a forma é que está errada — isso é `TypeError`. Colapsar as duas
categorias num tipo só obriga quem chama a inspecionar a **mensagem de texto**
para distinguir um caso do outro, e mensagem não é contrato: ela pode ser
reescrita a qualquer momento sem que ninguém considere isso uma quebra.

**Alteração realizada.**

```diff
     if not isinstance(dados, dict):
-        raise ValueError(
+        raise TypeError(
             "Série recusada: o arquivo não contém um objeto com os metadados "
             "da série."
         )
```

A docstring passou a declarar as duas exceções separadamente, e o teste do caso
passou a exigir `TypeError`.

**Teste executado.** `ruff check src tests`, a suíte versionada e uma **campanha
de mutação** com sete mutações sobre `src/devops.py` — rótulo aceito sem
verificação, crescimento sem saturação, pesos trocados, taxa de falha sobre a
fase errada, arredondamento reduzido, série vazia aceita e piso do crescimento
removido.

**Resultado obtido.**

```text
antes  ->  ruff: TRY004 em src/devops.py, 1 error
depois ->  ruff: All checks passed!
suite versionada    -> 364 passed  (345 -> 364)
campanha de mutacao -> 7 mutacoes, 7 detectadas pela suite versionada
```

A lição é sobre o que uma recusa comunica: recusar é fácil, recusar **na
categoria certa** é o que torna a recusa utilizável. Quem precise tratar
"arquivo corrompido" de um jeito e "série mal preenchida" de outro consegue
fazê-lo por `except`, sem ler texto de mensagem — e o texto segue livre para
mudar sem quebrar ninguém.

### Ciclo 22 — o fluxo exportado não sobrevivia a uma importação real (E09)

**Problema observado.** O arquivo do fluxo passava em toda a verificação
estrutural — JSON válido, três nós, tipos corretos, encadeamento conferido — e
mesmo assim **não era importável**. A tentativa real, pela linha de comando da
ferramenta, parou antes de criar o fluxo:

```text
Importing 1 workflows...
An error occurred while importing workflows.
SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id
```

Corrigido isso, a **execução** falhou no segundo nó:

```text
NodeApiError: The service refused the connection - perhaps it is offline
httpCode: ECONNREFUSED
connect ECONNREFUSED ::1:8000
```

**Diagnóstico.** Dois defeitos independentes, nenhum deles detectável sem
executar de verdade:

| Defeito | Causa |
|---|---|
| Importação recusada | o arquivo não trazia o campo `id` de topo. O schema aceito pela importação o exige; a validação por `json.loads` nunca cobriria isso, porque o arquivo **é** JSON válido |
| Conexão recusada | o endereço do nó de integração usava `localhost`. Em Node 24 esse nome resolve primeiro para `::1`, e a aplicação, ligada a `127.0.0.1`, recusa a conexão nesse endereço |

O segundo caso é o mais instrutivo: `localhost` e `127.0.0.1` parecem
intercambiáveis e não são. A resolução depende do sistema, da versão do runtime
e da ordem das famílias de endereço — três coisas que o arquivo exportado não
controla.

**Alteração realizada.**

```diff
 {
+  "id": "javalog-agent-lowcode",
   "name": "JavaLog Agent - analise de log por webhook",
```

```diff
-        "url": "http://localhost:8000/api/v1/analyze",
+        "url": "http://127.0.0.1:8000/api/v1/analyze",
```

Cada correção ganhou um teste versionado que a guarda: um exige o campo de topo,
outro exige endereço IPv4 explícito e porta, e um terceiro recusa qualquer nó
que volte a apontar para `localhost`.

**Teste executado.** Importação e execução reais numa instância local da
ferramenta, mais a suíte versionada e a verificação da etapa.

**Resultado obtido.**

```text
antes  ->  importacao: SQLITE_CONSTRAINT  |  execucao 1: error, ECONNREFUSED ::1:8000
depois ->  importacao: Successfully imported 1 workflow
           execucao 2: success  -> HTTP 200, diagnostico completo
           execucao 3: success  -> HTTP 200, erro de dominio propagado no corpo

Webhook Trigger      success    0 ms
HTTP Request         success  738 ms
Respond to Webhook   success    6 ms

suite versionada -> 383 passed  (380 -> 383)
```

A lição é sobre o limite da verificação estrutural: **um artefato de integração
só está comprovado quando o sistema de destino o aceita e o executa**. Os testes
de forma diziam a verdade sobre o arquivo e, ainda assim, não diziam nada sobre
o que aconteceria na importação — porque a forma estava certa e o contrato do
destino era outro.

### Ciclo 23 — a documentação negava uma escrita que o próprio agente faz (E10)

**Problema observado.** Seis documentos afirmavam que a execução bloqueada não
escreve nada. As formulações variavam — *"nenhum arquivo é escrito"*, *"não há
escrita em disco"*, *"zero arquivo criado"*, *"nada escrito"*, *"`output/`
permanece com o mesmo conteúdo"*, *"não produz efeito fora do estado"* — e todas
diziam a mesma coisa falsa. A verificação direta, contando linhas antes e depois
de uma execução bloqueada:

```text
codigo de saida    : 1
agent-events.jsonl : 72 -> 73  (delta 1)
agent-audit.jsonl  : 72 -> 73  (delta 1)
report_*.md        :  1 ->  1  (delta 0)
```

**Diagnóstico.** Duas afirmações diferentes tinham sido fundidas numa só. É
verdade que o caminho bloqueado não chama o modelo, não gera relatório de
diagnóstico e não executa ação externa. Não é verdade que ele não escreva: toda
rota passa por `finalizar_execucao`, e esse nó emite uma linha em cada um dos
dois sinais **de propósito**. A escrita que sobra não é vazamento do bloqueio, é
a condição para que o bloqueio seja investigável.

O erro tinha consequência maior que a imprecisão: quem lesse a documentação e
depois inspecionasse `output/` encontraria linhas que o texto dizia não existir —
e passaria a duvidar do resto.

**Alteração realizada.** As seis afirmações foram substituídas por uma
formulação que separa as quatro grandezas: zero relatório de diagnóstico, zero
chamada ao modelo, zero ação externa e **emissão intencional dos dois sinais**.
Em `docs/seguranca/cenario-adversarial.md`, a linha da tabela comparativa foi
desdobrada em duas, porque uma linha só não conseguia dizer a verdade sobre as
duas coisas:

```diff
-| Escritas em `output/` | 1 | **0** |
+| Relatório de diagnóstico gerado | 1 | **0** |
+| Sinais de observabilidade emitidos | 2 | 2 |
```

O teste que guardava esse comportamento chamava-se
`test_cenario_adversarial_nao_escreve_nada`, e o nome prometia mais do que o
corpo verificava: ele observa a tool de relatório, não todas as escritas do
sistema. Passou a chamar-se `test_cenario_adversarial_nao_escreve_relatorio`,
sem alteração de comportamento.

**Teste executado.** Contagem das linhas dos dois sinais antes e depois de uma
execução bloqueada real, mais a suíte versionada.

**Resultado obtido.**

```text
execucao bloqueada -> 1 linha em cada sinal, 0 relatorio, codigo de saida 1
suite versionada   -> 413 passed  (413 -> 413; apenas o nome do teste mudou)
```

A lição é sobre o que um nome de teste promete: **um teste chamado "não escreve
nada" que observa apenas uma tool vira evidência de uma afirmação que ele nunca
fez**. Esse nome vazou para seis documentos e virou fato declarado.

### Ciclo 24 — números de contagem envelheceram sem que nada os conferisse (E10)

**Problema observado.** Três contagens publicadas divergiam do estado real da
árvore:

| Onde | Publicado | Real |
|---|---:|---:|
| `docs/evidencias/pacote.md`, linha de `docs/` | 32 | **33** |
| `docs/evidencias/scans.md`, arquivos inspecionados | 77 | **80** |
| soma das parcelas da tabela de distribuição | 79 | **80** |

A mesma tabela declarava **80 arquivos** no cabeçalho e somava 79 nas linhas.

**Diagnóstico.** Número escrito à mão em prosa não tem quem o recuse quando o
mundo muda. As etapas seguintes acrescentaram arquivos a `docs/` e as contagens
ficaram onde estavam — nenhum teste as lia, nenhum verificador as comparava com
`git ls-files`. O caso mais revelador é o da soma: o total estava certo, as
parcelas erradas, e a contradição vivia dentro da mesma tabela sem nunca ter
sido somada por ninguém.

**Alteração realizada.** `docs/` passou a 33, o scanner passou a declarar 80
arquivos inspecionados, e a soma das parcelas foi conferida contra o total.

**Teste executado.** Contagem por pasta a partir de `git ls-files` somado aos
arquivos novos não ignorados, e soma aritmética das parcelas da tabela.

**Resultado obtido.**

```text
docs 33 · tests 15 · src 15 · examples 9 · raiz 5 · slides 1 · output 1 · .github 1
soma das parcelas = 80    total declarado = 80    rastreados + novos = 80
```

A lição: **um total que ninguém soma é uma afirmação, não uma verificação.**

### Ciclo 25 — os comandos de ambiente virtual não rodavam onde diziam rodar (E10)

**Problema observado.** Três sequências de instalação publicadas eram
inexecutáveis ou ambíguas no ambiente que anunciavam:

| Onde | Comando publicado | O que acontece |
|---|---|---|
| `README.md`, seção *Linux, macOS ou Git Bash* | `source .venv/bin/activate` | falha no Git Bash sobre Windows: o ambiente criado ali é o do Windows, e os executáveis ficam em `.venv/Scripts` |
| `docs/evidencias/instalacao-e-sintaxe.md` | bloco marcado como `bash` com sintaxe de PowerShell dentro | linguagem do bloco contradiz o comando, e faltava o prefixo que o PowerShell exige para executar do diretório corrente |
| `docs/evidencias/pacote.md`, sequência do clone | `python -m venv .venv` seguido de `python -m pip install` | cria o ambiente e **nunca o ativa**: as linhas seguintes rodam no Python global |

**Diagnóstico.** O terceiro caso é o pior, porque **funciona**. Instalar e testar
com o interpretador global não produz erro nenhum: produz um resultado que não
prova o que a seção promete provar, que é o clone limpo se sustentando sozinho.
Comando que falha é detectado na primeira tentativa; comando que passa pelo
motivo errado sobrevive até alguém com outro ambiente tentar reproduzir.

O primeiro caso vem de tratar Git Bash como se fosse Unix. É um shell POSIX
sobre Windows: a sintaxe é a de Bash, a árvore do ambiente virtual é a do
Windows. As duas coisas não andam juntas.

**Alteração realizada.** *Linux ou macOS* e *Git Bash sobre Windows* passaram a
ser seções separadas, cada uma com o caminho de ativação que existe naquele
sistema. O bloco de PowerShell foi remarcado como `powershell` e recebeu o
prefixo exigido. A sequência do clone passou a invocar o interpretador do
ambiente virtual **pelo caminho**, dispensando ativação, em duas variantes por
plataforma. A seção da API passou a declarar as duas situações — sem `.env`, o
diagnóstico conclui em `fallback`; com `--env-file .env`, em `llm` — sem tornar o
arquivo obrigatório.

**Teste executado.** Duas das quatro sequências foram executadas; as outras duas
não podiam ser, e ficam declaradas como não executadas.

| Sequência | Situação | O que foi feito |
|---|---|---|
| **Windows PowerShell** | **executada** | interpretador do ambiente virtual invocado pelo caminho, com a suíte inteira |
| **Git Bash sobre Windows** | **executada** | ativação por `source .venv/Scripts/activate` e resolução do interpretador |
| **Linux ou macOS** | **não executada** | revisada apenas documentalmente; este host é Windows e não há máquina Unix no ciclo |
| **Clone limpo a partir do remoto** | **não executada** | `origin/develop` está em `b8fd934` com **70 arquivos**; os 10 arquivos desta etapa ainda não foram integrados, então o clone que a seção descreve **ainda não existe** |

**Resultado obtido.**

```text
PowerShell  interpretador do venv pelo caminho     -> 413 passed
Git Bash    source .venv/Scripts/activate          -> ativa
            which python                           -> .venv/Scripts/python
            sys.prefix                             -> .venv
            .venv/bin/activate                     -> No such file or directory
Linux/macOS                                        -> NAO EXECUTADO neste host
clone limpo                                        -> NAO EXECUTADO; origin/develop
                                                      tem 70 arquivos, a arvore
                                                      candidata local tem 80
cenario adversarial (PowerShell)                   -> codigo de saida 1
```

O caso do Git Bash é o que fecha o argumento com medida, e não com raciocínio: a
ativação funciona por `Scripts`, o interpretador resolve para
`.venv/Scripts/python`, e `.venv/bin/activate` **não existe** — que era
exatamente o caminho publicado antes.

A lição tem duas metades, e a segunda custou mais. A primeira: **um comando de
documentação só está verificado quando foi executado no shell que ele nomeia.** A
segunda: **declarar como executado o que não foi executado é o mesmo defeito que
o ciclo se propôs a corrigir** — a primeira redação deste ciclo afirmava ter
rodado as quatro sequências, incluindo um clone do remoto que ainda não podia
existir. Uma seção de evidência que descreve reprodução futura é instrucional e
legítima; o que não é legítimo é registrá-la como medição já feita.

### Ciclo 26 — o diagrama nomeava nós que o grafo não registra (E11)

**Problema observado.** O diagrama de arquitetura e o texto que o acompanha
apresentavam `extrair_eventos` e `classificar_log` como as duas branches
paralelas. A comparação com os nós efetivamente registrados no `StateGraph`
mostrou outra composição:

```text
add_node registrados : analisar_excecoes · analisar_eventos · consolidar_analises · …
route_ler_log        : ["analisar_excecoes", "analisar_eventos"]
extrair_eventos      : definido em src/nodes.py, nao registrado como no
classificar_log      : definido em src/nodes.py, chamado dentro de consolidar_analises
```

As duas funções citadas existem — são herdadas do miniprojeto e continuam em uso
—, mas nenhuma delas é uma das branches paralelas. `extrair_eventos` não é
registrada como nó, e `classificar_log` executa **depois** do fan-in, dentro de
`consolidar_analises`.

**Diagnóstico.** A paralelização sempre esteve correta no código; o que
divergia era a **nomenclatura publicada**. O diagrama foi escrito a partir das
funções herdadas, e os nós de controle acrescentados depois receberam nomes
próprios sem que a documentação acompanhasse. O erro é de rastreabilidade: quem
lesse a arquitetura e fosse procurar `extrair_eventos` no grafo não o
encontraria, e quem lesse `classificar_log` como branch paralela concluiria que
a classificação ocorre antes da consolidação — quando ocorre dentro dela.

**Alteração realizada.** Nomes e responsabilidades alinhados ao fluxo
executável, em `README.md` e `docs/arquitetura.md`:

```diff
-    D --> E[extrair_eventos]
-    D --> F[classificar_log]
+    D --> E[analisar_excecoes]
+    D --> F[analisar_eventos]
```

A tabela de nós passou a descrever `analisar_excecoes` como a branch que extrai
as exceções Java, `analisar_eventos` como a que extrai as linhas `ERROR` e
`WARN`, e `consolidar_analises` como o fan-in que reúne as duas contribuições e
chama `classificar_log`. A seção de paralelização ganhou o caminho explícito, do
arquivo à categoria, e a ressalva de que a classificação não é uma terceira
branch paralela.

**Teste executado.** Um teste de regressão em `tests/test_graph_advanced.py`
confere, na mesma execução, a rota do grafo e o texto dos dois documentos: que
`route_ler_log` devolve exatamente as duas branches reais, que os dois nomes
aparecem em ambos os documentos, que `extrair_eventos` não é mais apresentado
como nó, que nenhum dos dois textos associa `classificar_log` a execução
paralela, e que ambos situam a classificação na consolidação.

**Resultado obtido.**

```text
antes  -> teste de regressao documental: FAILED (README com a nomenclatura anterior)
depois -> teste de regressao documental: PASSED
```

A lição é sobre o alcance de um teste de estrutura: a suíte já provava que a
paralelização existia e que as duas branches se reencontravam, mas nenhuma
verificação ligava o **nome publicado** ao **nó registrado**. Documentação de
arquitetura é afirmação sobre o código, e afirmação sobre o código pode ser
verificada por teste como qualquer outra.

### Ciclo 27 — as evidências publicadas ficaram atrás da suíte (E12)

**Problema observado.** Depois que o ciclo anterior acrescentou o teste
documental, as evidências de estado atual passaram a publicar uma contagem **uma
unidade abaixo** da suíte real. A verificação direta mostrou a diferença:

```text
pytest -q                                   -> 414 passed
docs/evidencias/testes.md, total declarado  -> uma unidade abaixo
soma das parcelas da tabela                 -> uma unidade abaixo
```

**Diagnóstico.** `tests/test_graph_advanced.py` passou de 32 para **33** testes,
e a suíte total passou para **414**. A tabela de distribuição e os totais
publicados são valores derivados da coleta da suíte e precisam ser
reconciliados sempre que essa coleta muda. As parcelas e o total permaneceram
consistentes entre si, mas deixaram de corresponder ao resultado real de
`pytest --collect-only`.

**Alteração realizada.** Cinco documentos, todos de estado atual:

| Documento | O que mudou |
|---|---|
| `README.md` | contagem de testes e total de ciclos |
| `docs/evidencias/testes.md` | saída do comando, parcela de `tests/test_graph_advanced.py`, total da tabela e a explicação do que a contagem mede |
| `docs/evidencias/instalacao-e-sintaxe.md` | resultado de `pytest -q` |
| `docs/evidencias/pacote.md` | resultado nas duas sequências de clone, PowerShell e Unix |
| `docs/evolucao-mini-projeto.md` | este ciclo e o total de ciclos |

Os registros históricos dos ciclos 23 e 25 **foram preservados** com a contagem
que era verdadeira quando foram escritos. Corrigi-los seria apagar a medição,
não atualizá-la.

**Teste executado.** `pytest -q`; `pytest --collect-only` para a contagem por
arquivo; soma executável das parcelas da tabela conferida contra o total
declarado; e busca global pelas duas contagens em todo o conjunto versionável,
separando as ocorrências de estado atual das históricas.

**Resultado obtido.**

```text
pytest -q                                  -> 414 passed
tests/test_graph_advanced.py               -> 33 testes coletados
soma das parcelas = total declarado        -> 414 = 414
ocorrencias de estado atual desatualizadas -> 0
ocorrencias historicas preservadas         -> 2 (ciclos 23 e 25)
```

A lição é que valores derivados da suíte precisam ser revalidados sempre que a
coleta de testes muda. A distribuição por arquivo e o total publicado devem ser
comparados tanto entre si quanto com o resultado de `pytest --collect-only`.

## Resultado consolidado da E01

| Verificação | Resultado |
|---|---|
| Arquivos da baseline transportados | 36 de 36 |
| Artefatos locais transportados | nenhum |
| Prompts `01` a `09` após normalização | 9 de 9 idênticos |
| Contagens de referência dos três logs | 1/1 · 2/1 · 0/0, conforme congelado |
| `python -m compileall -q src tests` | exit 0 |
| `ruff check src tests` | `All checks passed!` |
| `pytest -q` sem rede e sem chave | `26 passed` |
| `pip check` | `No broken requirements found` |
| Varredura de segredos | zero ocorrências, com **dois** controles negativos, um deles no `.env.example` |
| Validação complementar da E01 | **38 checagens, 0 falhas** |

## Fechamento

### O que aconteceu com a baseline

| Categoria | Quantidade | Observação |
|---|---:|---|
| **Mantido** | 22 arquivos | prompts históricos, logs, relatórios de referência, slides e os contratos herdados |
| **Refatorado** | 14 arquivos | ampliados sem quebrar nome público, mensagem literal nem comportamento herdado |
| **Adicionado** | 44 arquivos | as capacidades novas e a documentação que as sustenta |
| **Removido** | **0** | nada da baseline foi descartado |

**80 arquivos** no total. Cada arquivo herdado que mudou continua passando nos
testes que já existiam antes da mudança — foi essa a regra que governou toda a
refatoração.

### Os ciclos de refinamento

**27 ciclos reais** estão registrados acima, cada um com problema observado,
diagnóstico, alteração rastreável, teste ou lint executado e resultado obtido.
Eles não foram reconstruídos no fim: cada um foi escrito no momento em que
aconteceu.

O que eles têm em comum vale mais que a soma:

| Padrão recorrente | Onde apareceu |
|---|---|
| **Teste ancorado na própria constante que deveria guardar** | ciclos 12, 16 e 18 — o teste acompanhava a mudança em vez de recusá-la |
| **Verificação que afirma mais do que executa** | ciclos 8 e 9 — cobertura aparente com ponto cego real |
| **Erro de fronteira em condição de limite** | ciclos 5 e 13 — igualdade e precedência, onde os operadores divergem |
| **Campo publicado sem produtor** | ciclo 20 — omitir é honesto, zerar é falso |
| **Artefato válido que o destino recusa** | ciclo 22 — forma correta, contrato do destino diferente |
| **Documentação que afirma mais do que o código faz** | ciclos 23 e 24 — a prosa envelheceu sem que nada a recusasse |
| **Comando que passa pelo motivo errado** | ciclo 25 — o clone instalava no interpretador global e ainda assim terminava sem erro |
| **Nome publicado que não corresponde ao registrado** | ciclo 26 — o diagrama descrevia o fluxo certo com os nomes errados |
| **Contagem derivada sem reconferência da fonte** | ciclo 27 — soma por arquivo e total reconciliados com `pytest --collect-only` |

### O que a evolução preservou

Nenhuma capacidade do miniprojeto foi perdida. O agente continua validando,
lendo de forma confinada, extraindo, classificando, diagnosticando e gravando o
relatório — e continua **concluindo sem chave de modelo**. Tudo o que veio depois
foi acrescentado em torno disso, sem substituir o que já funcionava.

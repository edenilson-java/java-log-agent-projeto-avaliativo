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
| Mensagens literais de erro, acesso negado e extensão inválida | Conferidas **caractere a caractere**, com acentuação | seção [7] de `v01-fundacao.py` |
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
| `tests/test_tools.py` (E03) | Portabilidade de caminho e recusa de tipo errado | fecham pontos cegos revelados por mutação e por auditoria |

## Adicionado

| Componente | Finalidade | Evidência |
|---|---|---|
| `src/config.py` | Configuração tipada e imutável por variável de ambiente, com a chave em `SecretStr` | **13 verificações** em `v01-fundacao.py`, seções [4] e [5] |
| `docs/evolucao-mini-projeto.md` | Este documento | — |
| `tests/test_graph_advanced.py` (E02) | Cobertura do que a evolução acrescentou ao fluxo | 28 testes; 3 mutações deliberadas detectadas |
| `src/api.py` (E03) | API local FastAPI: `/health`, tool read-only e análise | 200/400/409/422 comprovados |
| `src/mcp_server.py` (E03) | Servidor MCP local por stdio, somente a capability `read_log` | read-only comprovado: não grava e não chama o modelo |
| `tests/test_api.py` (E03) | Integração pela fronteira HTTP e CLI | 35 testes |
| `tests/test_mcp.py` (E03) | Integração pela fronteira MCP, in-process, atravessando `call_tool` | 22 testes |

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
do script da etapa: as mensagens `system` e `user` são renderizadas com valores sintéticos
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

**Correção posterior, apontada em auditoria.** A primeira versão do scanner mantinha uma
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
`test_branches_nao_executam_no_erro_de_leitura` e o script `v02-grafo.py`; e uma **mutação
deliberada** revertendo o fan-out para a forma descartada.

**Resultado obtido.**

```text
forma adotada, caminho de erro  ->  achados: []  (nenhuma branch executou)
mutação de volta à forma antiga ->  1 failed, 8 passed   (o teste detecta)
suíte completa                  ->  54 passed
```

### Ciclo 4 — a verificação de transporte acusava falsa divergência (E02)

**Problema observado.** Ao rodar o verificador da E01 como teste de regressão dentro da
E02, ele reprovou apontando cinco arquivos supostamente corrompidos, entre eles o prompt
histórico `01` e os três logs de exemplo — justamente os arquivos que **não podem** mudar.

**Diagnóstico.** O conteúdo **versionado** estava intacto. O `git show HEAD:` do prompt `01`
devolve `CRLF=0` e `776 bytes`, idêntico à baseline. O que diverge é a **árvore de
trabalho**: no Windows o Git converte LF para CRLF no checkout.

| Arquivo | Baseline | Árvore de trabalho | Bruto igual? | Normalizado igual? |
|---|---|---|---|---|
| `docs/prompts/01-...md` | 21 LF, 776 bytes | 21 CRLF, 797 bytes | não | **sim** |
| `examples/logs/null-pointer-exception.log` | 6 LF, 490 bytes | 6 CRLF, 496 bytes | não | **sim** |

O defeito era do verificador: a seção de transporte comparava **bytes brutos**, enquanto o
plano determina comparação **após normalizar fim de linha**. A seção dos prompts já
normalizava corretamente; a de transporte, não.

**Alteração realizada.** A comparação de transporte passou a normalizar fim de linha, e foi
declarado o conjunto `REFATORADOS_E02` com os arquivos que a E02 legitimamente alterou, para
que o script siga falhando se qualquer outro arquivo divergir sem declaração.

**Teste executado.** `v01-fundacao.py` reexecutado como regressão dentro da E02.

**Resultado obtido.**

```text
antes da correção  ->  2 FALHA(S): 5 arquivos "divergentes inesperados"
após a correção    ->  TODAS AS VERIFICACOES DA E01 PASSARAM  (38 checagens, exit 0)
```

Este ciclo confirma, na prática, duas decisões tomadas antes: escrever os arquivos em modo
binário no transporte, e a exigência do plano de que a comparação dos nove prompts seja
sempre feita após normalização.

### Ciclo 5 — erro de fronteira no limite de passos, encontrado pela auditoria (E02)

**Problema observado.** A auditoria independente reprovou a E02 apontando que

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
| `arquivos/execucao/v02-grafo.py` | verificação da igualdade na rota isolada **e** no fluxo completo |

Para provar que o modelo não é acionado, foi criada uma subclasse local `ContandoLLM` com
contador de chamadas, em vez de alterar o `fake_llm.py` herdado.

**Teste executado.** Suíte completa, verificador da etapa, e uma **mutação deliberada**
revertendo o operador para `>`.

**Resultado obtido.**

```text
fronteira, os dois lados:
  step=31 max=32 -> continuar     step=32 max=32 -> limite
  step=9  max=10 -> continuar     step=10 max=10 -> limite

pytest -q            ->  58 passed
v02-grafo.py         ->  62 checagens, 0 falhas, exit 0

com o operador revertido para '>':
  v02-grafo.py       ->  exit 1  — FALHOU route_inicializar: limite NA IGUALDADE
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

**Teste executado.** `tests/test_mcp.py`, in-process, mais o script `v03-tool.py`.

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

### Ciclo 8 — a suíte entregue tinha ponto cego que só o script pegava (E03)

**Problema observado.** O teste de mutação da E03 revelou algo mais grave que uma regra de
lint. Das três mutações aplicadas, **duas foram detectadas apenas pelo script de
verificação** — que vive em `arquivos/execucao/` e **não é entregue**:

| Mutação | Script `v03` | Suíte versionada |
|---|---|---|
| `cancelled` deixa de mapear para 409 | detectou | **detectou** |
| `as_posix()` revertido para `str(path)` | detectou | **cega** |
| CLI para de propagar `blocked`/`cancelled` | detectou | **cega** |

Ou seja: quem clonasse o repositório e rodasse `pytest` teria a suíte verde com duas
regressões reais presentes.

**Alteração realizada.** Quatro testes acrescentados à suíte **versionada**:

- `tests/test_tools.py`: portabilidade do caminho devolvido por
  `write_diagnostic_report` e por `read_log_as_response`;
- `tests/test_api.py`, seção *Fronteira CLI*: código de saída para os seis desfechos
  possíveis e preservação das linhas literais da CLI.

Os testes de CLI ficaram em `test_api.py` porque a árvore entregável prevista no plano
**não contempla** um `test_cli.py`, e acrescentar um 81º arquivo exigiria emenda ao plano.

**Teste executado.** As três mutações foram reaplicadas, agora rodando **somente** a suíte
versionada.

**Resultado obtido.**

```text
as_posix() revertido em write_diagnostic_report  ->  1 failed, 108 passed
CLI para de propagar blocked/cancelled           ->  2 failed, 107 passed
as_posix() revertido no contrato estruturado     ->  1 failed, 108 passed
```

A lição é sobre onde a garantia mora: **verificação que não é entregue não protege o
projeto entregue**. O script de etapa é ferramenta de desenvolvimento; o que defende o
repositório é a suíte versionada.

### Ciclo 9 — rótulo do verificador ficou factualmente falso (E03)

**Problema observado.** O verificador da E01 classificava `src/tools.py`, `src/main.py` e
`tests/test_tools.py` como **"corrigidos só por lint"**. Depois que a E03 fez mudanças
**funcionais** nesses mesmos arquivos, o rótulo passou a afirmar algo falso — e o script
continuava aprovando, porque a checagem só olhava o conjunto, não o motivo.

**Alteração realizada.** Criado o conjunto `REFATORADOS_E03`, com nota explícita de que um
arquivo pode aparecer em mais de um conjunto: correção de lint na E01 e mudança funcional na
E03 são coisas diferentes sobre o mesmo arquivo.

**Resultado obtido.** O relatório do verificador passou a distinguir as quatro categorias, e
segue reprovando se qualquer arquivo divergir sem declaração:

```text
..  corrigidos so por lint : ['src/main.py', 'src/nodes.py', 'src/tools.py', ...]
..  refatorados na E02     : ['src/graph.py', 'src/nodes.py']
..  refatorados na E03     : ['src/main.py', 'src/schemas.py', 'src/tools.py', 'tests/test_tools.py']
```

Um verificador que aprova com rótulo errado é pior que um que reprova: ele documenta uma
inverdade e ninguém percebe.

### Ciclo 10 — três lacunas de fronteira encontradas pela auditoria (E03)

**Problema observado.** A auditoria independente reprovou a E03 com três achados objetivos,
todos reproduzidos antes de qualquer correção.

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

**Teste executado.** Suíte completa, verificador da etapa reescrito para usar `call_tool`, e
três mutações deliberadas — uma por lacuna.

**Resultado obtido.**

```text
pytest -q      ->  124 passed
v03-tool.py    ->  97 checagens, 0 falhas, exit 0

mutacoes, contra a suite VERSIONADA:
  remove a validacao de tipo          ->  7 failed, 117 passed
  blocked deixa de mapear para 409    ->  2 failed, 122 passed
  MCP expoe capability de escrita     ->  2 failed, 122 passed
```

A lição repete a do Ciclo 8, num nível acima: **testar o handler não é testar a integração**.
As três lacunas tinham a mesma raiz — verificar o componente isolado e chamar isso de
fronteira. A fronteira só está testada quando o teste passa por ela.

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
| Script `v01-fundacao.py` | **38 checagens, 0 falhas** |

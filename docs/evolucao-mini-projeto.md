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

## Adicionado

| Componente | Finalidade | Evidência |
|---|---|---|
| `src/config.py` | Configuração tipada e imutável por variável de ambiente, com a chave em `SecretStr` | **13 verificações** em `v01-fundacao.py`, seções [4] e [5] |
| `docs/evolucao-mini-projeto.md` | Este documento | — |

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

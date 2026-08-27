# Logs do pipeline no GitHub Actions

Evidência do **primeiro run real** do pipeline, executado pelo GitHub Actions
após a publicação da branch. Os trechos abaixo são recortes literais do log do
run, com os carimbos de tempo originais.

## O run

| Campo | Valor |
|---|---|
| Run | **33120768726** |
| Link | https://github.com/edenilson-java/java-log-agent-projeto-avaliativo/actions/runs/33120768726 |
| Workflow | `CI` (`.github/workflows/ci.yml`) |
| Disparo | `push` na branch `feature/devops-anomalias` |
| Commit | `33855c650ef2f415fc6b59d99466123cac54253e` |
| Conclusão | **`success`** |
| Início · fim | `2026-08-27T22:01:38Z` · `2026-08-27T22:02:44Z` |
| Duração do job | **1 min 2 s** |
| Runner | `windows-latest`, versão 2.336.0 |
| Interpretador | Python 3.12.10 |
| Shell dos passos | PowerShell 7 |

Todos os sete passos executados terminaram em `success`:

```text
1. Set up job                success
2. Obter o codigo            success
3. Preparar o Python         success
4. Instalar dependencias     success
5. Lint                      success
6. Testes                    success
7. Compilacao                success
```

## Etapa 1 — Lint

Recorte literal do log do run:

```text
2026-08-27T22:02:26.4374796Z ##[group]Run ruff check src tests
2026-08-27T22:02:26.4375156Z ruff check src tests
2026-08-27T22:02:26.4477890Z shell: C:\Program Files\PowerShell\7\pwsh.EXE -command ". '{0}'"
2026-08-27T22:02:26.4478537Z   pythonLocation: C:\hostedtoolcache\windows\Python\3.12.10\x64
2026-08-27T22:02:26.4480544Z ##[endgroup]
2026-08-27T22:02:26.7261226Z All checks passed!
```

A etapa levou **0,29 s** entre o fim do cabeçalho e a linha de resultado.

## Etapa 2 — Testes

Recorte literal do log do run:

```text
2026-08-27T22:02:26.8647976Z ##[group]Run pytest -q --disable-warnings
2026-08-27T22:02:26.8648457Z pytest -q --disable-warnings
2026-08-27T22:02:26.8750253Z shell: C:\Program Files\PowerShell\7\pwsh.EXE -command ". '{0}'"
2026-08-27T22:02:26.8750864Z   pythonLocation: C:\hostedtoolcache\windows\Python\3.12.10\x64
2026-08-27T22:02:26.8752914Z ##[endgroup]
2026-08-27T22:02:32.9758619Z ........................................................................ [ 19%]
2026-08-27T22:02:34.1343599Z ........................................................................ [ 39%]
2026-08-27T22:02:35.4832637Z ........................................................................ [ 59%]
2026-08-27T22:02:36.3601718Z ........................................................................ [ 79%]
2026-08-27T22:02:37.2081230Z ........................................................................ [ 98%]
2026-08-27T22:02:37.4436834Z ....                                                                     [100%]
2026-08-27T22:02:37.4437303Z 364 passed in 7.73s
```

## Etapa 3 — Compilação

```text
2026-08-27T22:02:37.9865049Z ##[group]Run python -m compileall -q src
2026-08-27T22:02:37.9865444Z python -m compileall -q src
2026-08-27T22:02:37.9964310Z shell: C:\Program Files\PowerShell\7\pwsh.EXE -command ". '{0}'"
2026-08-27T22:02:37.9966967Z ##[endgroup]
```

`compileall -q` só imprime quando encontra erro de sintaxe. A ausência de saída,
com o passo concluído em `success`, é o resultado esperado.

## Comparação com a execução local

O mesmo comando, sobre o mesmo commit, nos dois ambientes:

| Etapa | Local | GitHub Actions |
|---|---|---|
| Lint | `All checks passed!` | `All checks passed!` |
| Testes | `364 passed` | `364 passed` |
| Compilação | sem saída, código 0 | sem saída, `success` |

O número de testes coincide: **364 em ambos**, sem teste pulado em nenhum dos
dois. A diferença de tempo da suíte — 5,58 s local contra 7,73 s no runner — é
de ambiente, e não altera nenhum resultado.

O pipeline roda **sem credencial configurada**: o workflow não declara `secrets.`
nem variável de chave, e a suíte percorre inteira o caminho sem modelo.

## Aviso emitido pelo run

O run registrou uma anotação, que **não** afeta a conclusão:

```text
Node.js 20 is deprecated. The following actions target Node.js 20 but are being
forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5.
```

É um aviso da plataforma sobre o runtime das ações usadas, não do código deste
repositório. As ações continuam funcionando, executadas sobre Node.js 24. Fica
registrado aqui porque um aviso silenciado é um aviso que ninguém revisita: a
atualização das ações para versões que declarem Node.js 24 é a ação futura
indicada, e não havia como antecipá-la sem um run real.

## Recorte transcrito, não resumido

Os blocos acima preservam carimbo de tempo, ordem e texto do log do run. A única
alteração foi a remoção dos códigos de cor do terminal (`ESC[36;1m`) na linha em
que a plataforma repete o comando, que de outro modo apareceriam como bytes
ilegíveis. Nenhuma linha de resultado foi editada, reordenada ou omitida.

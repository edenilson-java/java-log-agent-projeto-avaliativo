# Análise assistida por IA dos logs de lint e de testes

Análise dos dois logs reais registrados em
[`log-lint.md`](log-lint.md) e [`log-testes.md`](log-testes.md). As duas etapas
foram escolhidas por serem as que produzem sinal interpretável a cada execução:
lint mede forma, testes medem comportamento.

## Método

A leitura foi conduzida por três perguntas, aplicadas a cada log:

1. **o que a saída afirma?** — o resultado literal, sem paráfrase generosa;
2. **o que a saída não afirma, mas é fácil supor que afirma?** — a diferença
   entre passar e estar correto;
3. **o que mudaria a leitura na próxima execução?** — o que observar para que o
   log continue informativo em vez de virar ruído verde.

## Etapa 1 — lint

**O que a saída afirma.** `All checks passed!`, código `0`. Nenhuma violação nos
15 arquivos de `src/` e nos 13 de `tests/`.

**O que ela não afirma.** Que o código faz a coisa certa. Lint é uma verificação
de forma: reconhece import não usado, nome indefinido, construção suspeita. Um
módulo pode passar no lint inteiro e calcular a métrica errada.

**Leitura interpretativa.** Um log de lint limpo é o resultado esperado, e por
isso o valor dele está na **transição**: a linha só é informativa no dia em que
deixa de estar vazia. O ponto de atenção real é o oposto do óbvio — uma equipe
que se acostuma com `All checks passed!` para de ler a saída, e a primeira
violação passa despercebida no meio do log. É por isso que o passo é uma etapa
separada do pipeline, com falha própria, em vez de estar embutido na etapa de
testes: o pipeline para no lint, e não há como não ver.

**Sinal ausente que vale registrar.** A saída não traz contagem de arquivos
analisados. Se o comando um dia apontar para o diretório errado, ele imprimirá
exatamente a mesma linha de sucesso — um sucesso vazio é indistinguível de um
sucesso real nessa saída. A defesa contra isso não está no log, está no workflow:
o escopo `src tests` é literal e versionado, e mudá-lo aparece no diff.

## Etapa 2 — testes

**O que a saída afirma.** 364 testes executados, todos aprovados, em 5,58 s,
código `0`. A matriz de pontos não contém `F`, `E`, `s` nem `x`: nenhuma falha,
nenhum erro de coleta, nenhum teste pulado, nenhuma falha esperada.

**O que ela não afirma.** Que a cobertura é suficiente. `364 passed` mede quantos
testes existem e passaram, não quanto do comportamento eles observam. Um teste
que se ancora na própria constante que deveria proteger aparece nesta linha como
mais um ponto verde.

**Leitura interpretativa.** A ausência de `s` é o achado mais útil desta saída.
Suítes que crescem tendem a acumular testes pulados por condição de ambiente —
"pula se não houver chave", "pula se não houver rede" — e cada pulo transforma
uma garantia em intenção. Aqui não há nenhum, e isso é coerente com o modo como
a suíte foi construída: o caminho sem chave e sem rede é o caminho **normal** de
execução, não um modo degradado. É o que permite ao pipeline rodar sem
credencial alguma configurada.

## Correlação entre as duas etapas

As duas saídas são independentes por construção — lint não importa o código, e os
testes não avaliam estilo — e é essa independência que dá valor à combinação:

| Combinação observável | Leitura |
|---|---|
| lint verde · testes verdes | estado atual: forma e comportamento aprovados |
| lint verde · testes vermelhos | defeito de comportamento; o lint não tem como pegar |
| lint vermelho · testes verdes | forma degradada com comportamento intacto — é onde entra dívida silenciosa |
| lint vermelho · testes vermelhos | provável erro de sintaxe ou import quebrado; a terceira etapa, de compilação, distingue |

A terceira etapa do pipeline — `python -m compileall -q src` — existe para essa
última linha: ela separa "o código não compila" de "o código compila e está
errado", que é uma distinção cara de fazer lendo apenas falha de teste.

## Conclusão

Os dois logs mostram um estado aprovado, e o valor da análise não está em
celebrá-lo, e sim em registrar **o que cada saída não prova**. Lint verde não é
correção; suíte verde não é cobertura. As duas confusões são as que fariam
alguém tirar a conclusão errada destes mesmos logs na próxima execução.

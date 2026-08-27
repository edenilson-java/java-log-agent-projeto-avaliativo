# Priorização de testes por risco

Nem todo cenário custa o mesmo quando falha. Este documento ordena os cenários
do projeto por criticidade e impacto, e declara qual é o prioritário.

## Cenário prioritário

**O bloqueio adversarial é o cenário prioritário.**

### Por que ele

**É a primeira barreira determinística antes do modelo.** A política é avaliada
entre o fan-in das análises e a decisão de diagnóstico. Até ali, tudo o que
aconteceu foi validação de caminho e leitura confinada; a partir dali, o
conteúdo do arquivo passa a influenciar o que o agente faz. O bloqueio é o
ponto em que essa influência é examinada, e é determinístico — não depende do
modelo, de rede nem de chave.

**Concentra as três famílias de conteúdo hostil.** `prompt_injection`,
`secret_request` e `external_action_request` são detectadas no mesmo ponto, e a
fixture adversarial exercita as três de uma vez. Nenhum outro cenário cobre
tanta superfície numa única execução.

**Sua falha teria o maior impacto sobre autonomia e segurança.** Conteúdo
hostil alcançaria a etapa de diagnóstico, e a garantia que o projeto oferece —
a de que conteúdo externo não substitui as regras da aplicação — deixaria de
valer. É essa garantia, e não um efeito colateral específico, que o bloqueio
existe para sustentar.

### O que continua valendo se o bloqueio falhar

Registrado por honestidade, porque a priorização não depende de exagerar a
consequência:

| Defesa | O que ela cobre, mesmo sem o bloqueio |
|---|---|
| Redação de credenciais | dez formatos de credencial são substituídos por `[REDACTED]` antes de qualquer prompt, arquivo, sinal ou resposta |
| Capabilities limitadas | a aplicação não oferece ao modelo ferramenta de rede, de deleção ou de ação externa — um pedido nesse sentido não tem como ser atendido |
| Confinamento de disco | leitura restrita a `examples/logs/`, escrita restrita a `output/`, com nome sanitizado |
| Credencial fora do repositório | a chave vive em variável de ambiente, encapsulada, e não é enviada ao modelo |

Essas defesas **reduzem o dano, mas não substituem o bloqueio**. Nenhuma delas
cumpre o requisito de recusar a ação e exigir **aprovação humana** — que é o
que o bloqueio faz, e o que o enunciado pede em limites de autonomia.

### O alcance da consequência, dito com precisão

O enunciado prevê quatro condições que anulam a avaliação independentemente dos
demais critérios: **plágio, credenciais expostas, artefatos inacessíveis e
código que o estudante não consiga explicar**. Entre elas, a única que o
produto poderia causar por si é a **exposição real de credencial** — e ela é
tratada pelos controles listados na tabela acima.

Uma ação não autorizada que passasse pelo bloqueio não constitui, isoladamente,
nenhuma dessas quatro condições. A prioridade deste cenário não se apoia nisso:
apoia-se em criticidade e impacto, que já bastam.

## Ordem de prioridade

| # | Cenário | Criticidade e impacto | Cobertura |
|---|---|---|---|
| **1** | **Bloqueio adversarial** | primeira barreira determinística antes do modelo; concentra as três famílias de conteúdo hostil; sua falha permitiria que conteúdo hostil alcançasse o diagnóstico e comprometeria a garantia de que conteúdo externo não substitui as regras da aplicação | `tests/test_security.py` — aceitação |
| 2 | Redação de credenciais | credencial em arquivo, prompt ou resposta; exposição real de segredo é a única condição global de nota zero que o produto pode causar | `tests/test_security.py` — dez formatos, pelo fluxo real |
| 3 | Confinamento de leitura e escrita | leitura fora de `examples/logs/` ou escrita fora de `output/` | `tests/test_tools.py`, `tests/test_validation.py` |
| 4 | Fallback do modelo | o agente deixaria de concluir quando a integração falha | `tests/test_resilience.py` — quatro formas de falha |
| 5 | Condições de parada | execução indefinida ou consumo sem limite | `tests/test_graph_advanced.py` |
| 6 | Correlação dos sinais | investigação deixa de reconstruir a execução | `tests/test_observability.py` |
| 7 | Isolamento por thread | dado de uma sessão aparece em outra | `tests/test_memory.py` |
| 8 | Contratos de fronteira | cliente recebe resposta malformada ou código errado | `tests/test_api.py`, `tests/test_mcp.py` |

## Como a prioridade se traduz em cobertura

O cenário prioritário é o mais coberto da suíte, por decisão explícita:

| Aspecto | Verificação |
|---|---|
| Bloqueio | `status == "blocked"`, `requires_human == True`, as três famílias sinalizadas |
| Mensagem | literal conferida **caractere a caractere**, com acentuação |
| Chamada ao modelo | contada e verificada como **zero** |
| Escrita | tool de escrita contada como **zero**; diretório de saída inexistente ao fim |
| Ordem | as seis etapas instrumentadas, provando que nada com efeito executa depois da política |
| Falso positivo | os três logs legítimos do projeto e sete linhas operacionais passam sem bloqueio |
| Fronteira da CLI | código de saída **1** e mensagem impressa |

A ausência de falso positivo entra na lista de propósito. Um bloqueio que
dispara sobre log legítimo é tão inútil quanto um que não dispara: o agente
deixaria de diagnosticar qualquer coisa, e a proteção seria descartada pelo
operador na primeira semana.

## O que essa priorização não significa

Não significa que os demais cenários sejam opcionais — todos têm cobertura
versionada e todos rodam na mesma suíte. Significa que, havendo conflito entre
esforço de teste e tempo, o bloqueio adversarial é o último a ceder, e que
qualquer alteração que o afete exige revisão específica antes de ser aceita.

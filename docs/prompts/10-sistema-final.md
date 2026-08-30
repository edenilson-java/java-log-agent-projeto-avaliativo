# Prompt 10 — sistema final

> **Prompt novo, acrescentado ao final da série.** Os prompts `01` a `09` são o
> registro histórico do miniprojeto e foram preservados byte a byte, sem
> reescrita, renumeração ou reformatação. Este `10` **não** foi inserido no meio
> da numeração: ele descreve o sistema no estado em que o projeto foi entregue,
> e por isso vem depois de todos.

## Contexto

Os prompts anteriores construíram o miniprojeto: estrutura, estado, ferramentas
seguras, validação, nós, grafo, testes, README e apresentação. Este descreve o
sistema **evoluído**, com as capacidades acrescentadas ao longo do projeto
avaliativo.

## Prompt

```text
Você vai trabalhar no JavaLog Agent, um agente de diagnóstico de logs Java e
Spring Boot, já implementado e em estado final. Antes de propor qualquer
alteração, respeite o que segue.

ARQUITETURA
O sistema é híbrido: o esqueleto é determinístico e há um único ponto de LLM,
opcional, na redação do diagnóstico. Sem chave, sem rede ou diante de falha, o
fluxo conclui por um fallback determinístico. O grafo é explícito, com rotas
condicionais sobre o estado, uma paralelização com fan-out e fan-in, condição de
parada por número de passos e um ponto único de término.

FRONTEIRAS
O mesmo grafo é acionado por três caminhos, sem duplicação de lógica: a CLI, a
API HTTP e um servidor MCP local read-only. Uma automação low-code chama a API
como qualquer outro cliente.

INVARIANTES QUE NÃO PODEM SER QUEBRADOS
- leitura restrita ao diretório de logs; escrita restrita ao diretório de saída;
- a chave do modelo vive em variável de ambiente, encapsulada, e nunca é escrita
  em arquivo, log, sinal ou resposta;
- toda credencial reconhecida é redigida antes de qualquer prompt, arquivo,
  sinal ou resposta;
- a política de autonomia é avaliada ANTES da decisão de diagnóstico; bloqueado
  o fluxo, nenhuma ação com efeito executa depois;
- todo desfecho passa pelo ponto único de término e emite exatamente uma linha
  em cada um dos dois sinais;
- a memória é isolada por identificador de thread, e o identificador público
  coincide com a chave real do checkpointer.

REGRAS DE TRABALHO
- não acrescente camada de abstração que o problema não peça;
- não introduza retry no modelo: uma tentativa, sem repetição;
- toda alteração de comportamento precisa de teste versionado que a observe;
- um teste nunca deve se ancorar na constante que ele deveria estar guardando —
  escreva o valor esperado literalmente no teste;
- dado simulado é rotulado no próprio dado, e o código recusa dado sem rótulo;
- nenhuma afirmação de execução, número ou evidência que não tenha ocorrido.

QUANDO ALTERAR
Explique o que muda, por que muda, qual teste passa a cobrir a mudança e o que
deixaria de ser verdade se a alteração fosse revertida.
```

## Por que este prompt é assim

**Ele lista invariantes, não tarefas.** Um prompt de tarefa envelhece na semana
seguinte; um prompt que declara o que não pode ser quebrado continua útil
enquanto o sistema existir.

**Ele nomeia a armadilha que apareceu de fato.** A regra sobre teste ancorado na
própria constante não é teórica: foi observada em campanhas de mutação deste
projeto, em que testes passavam por acompanharem a mudança em vez de recusá-la.

**Ele proíbe inventar evidência.** É a regra que separa um relatório útil de um
relatório bonito, e vale tanto para quem escreve código quanto para quem escreve
documentação.

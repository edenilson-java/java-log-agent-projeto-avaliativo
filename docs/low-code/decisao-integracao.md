# Decisão de integração low-code

Por que n8n, por que um fluxo de três nós, e o que foi deliberadamente deixado
de fora.

## A ferramenta

**n8n**, entre as opções de automação low-code, por três razões objetivas:

| Critério | Por que pesou |
|---|---|
| Formato exportável e legível | o fluxo é um **JSON versionável**, que entra no repositório e aparece no diff. Ferramentas cujo fluxo só existe dentro da plataforma não deixam artefato para revisar |
| Execução local, sem conta | sobe por `npx` na própria máquina; não exige cadastro, chave de plataforma nem envio de dados a terceiros — coerente com um projeto que não usa credencial no repositório. Foi assim que o fluxo desta etapa foi executado |
| Webhook e HTTP Request nativos | os dois nós de que este caso precisa são de primeira classe, sem plugin ou nó comunitário |

## O desenho: três nós, e por que não mais

```text
Webhook Trigger  ->  HTTP Request  ->  Respond to Webhook
```

**Webhook Trigger** é o gatilho. Torna a automação acionável por qualquer
cliente HTTP, sem acoplar a um agendador ou a um serviço específico.

**HTTP Request** é a integração real com a aplicação. Chama
`POST /api/v1/analyze` — o mesmo endpoint que a suíte exercita — e encaminha o
corpo recebido **sem alteração**.

**Respond to Webhook** é a saída observável. Devolve ao chamador o que a
aplicação respondeu, e é o que torna o efeito do fluxo visível de fora.

### A restrição que governa o desenho

**Nenhum nó do fluxo reimplementa lógica da aplicação.** Não há nó de código,
função, condicional, filtro nem atribuição. O corpo entra, é encaminhado e a
resposta volta.

Isso é decisão, não simplificação por preguiça. A alternativa — distribuir
validação ou classificação entre nós do fluxo — traria três custos concretos:

1. **Duplicação divergente.** A validação de caminho existe em
   `src/validation.py`, com testes. Uma segunda validação dentro do fluxo
   passaria a divergir na primeira mudança, e a versão do fluxo não teria teste.
2. **Regra fora do alcance dos testes.** A suíte versionada não executa nós de
   n8n. Lógica movida para lá sai da cobertura e deixa de ser verificada no
   pipeline.
3. **Dependência invertida.** O agente deve funcionar sem a automação. Com regra
   no fluxo, remover o n8n mudaria o comportamento — e a automação deixaria de
   ser uma porta de entrada para virar parte do produto.

O teste `test_workflow_nao_tem_no_que_execute_logica` guarda essa decisão de
forma executável: a presença de qualquer nó de código, condicional, filtro ou
atribuição reprova a suíte.

## Credenciais: nenhuma, por construção

O JSON exportado **não contém credencial alguma**, e isso é verificado por três
testes: nenhum nó declara `credentials`, nenhuma chave de segredo aparece no
texto do arquivo e nenhum valor com formato de segredo é encontrado.

Foi possível porque o endpoint chamado é **local e não autenticado**. Se um dia
a API exigir autenticação, o caminho correto é o cofre de credenciais do próprio
n8n — que guarda o segredo fora do JSON exportado —, e **nunca** um valor escrito
no arquivo versionado.

## O que este fluxo não é

- **não é orquestrador do agente**: o fluxo do agente é o grafo em `src/graph.py`;
  o n8n orquestra apenas a chamada HTTP;
- **não é dependência para executar a aplicação**: a aplicação funciona pela API,
  pela CLI e pelo servidor MCP sem que o n8n exista;
- **não é evidência de deploy**: o fluxo **foi executado** numa instância local,
  com identificador, status e sequência de nós registrados — mas execução local
  não é publicação nem disponibilidade contínua. O que foi e o que não foi
  comprovado está declarado em [`reproducao.md`](reproducao.md).

## Alternativas consideradas

| Alternativa | Por que foi descartada |
|---|---|
| Nó de código no fluxo, montando o corpo campo a campo | reintroduziria no orquestrador uma decisão sobre o formato de entrada, que é contrato da API e já tem teste |
| Agendador em vez de webhook | o enunciado pede **gatilho**; um agendador dispararia sozinho, sem entrada externa, e a saída observável ficaria mais frágil de demonstrar |
| Fluxo que lê o arquivo de log e envia o conteúdo | quebraria o confinamento de leitura: hoje o caminho é validado e lido pela aplicação, dentro de `examples/logs/`. Enviar conteúdo bruto pelo webhook contornaria essa proteção |
| Manter `localhost` na URL do nó HTTP | medido nesta etapa: em Node 24 o nome resolve primeiro para `::1`, e uma API ligada a `127.0.0.1` recusa a conexão. O endereço IPv4 explícito remove a dependência da ordem de resolução |
| Exportar o fluxo sem o campo `id` de topo | a importação pela CLI do n8n recusa o arquivo; o campo é obrigatório no schema aceito pelo `import:workflow` |
| Responder direto pelo webhook, sem o terceiro nó | a resposta sairia antes da chamada à aplicação, e a saída deixaria de refletir o diagnóstico — perderia justamente a observabilidade que o item exige |

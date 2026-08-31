# Reprodução da automação low-code

O fluxo foi **executado de verdade** numa instância local do n8n. Esta página
registra os pré-requisitos, as sequências completas de reprodução, a execução
observada e — com a mesma clareza — o que a evidência **não** cobre.

## Pré-requisitos

### Para a aplicação

| Requisito | Papel |
|---|---|
| **Python 3.12** | executa o agente |
| Dependências de `requirements.txt` | `pip install -r requirements.txt` |

Isso basta para a **CLI**, a **API** e o **servidor MCP**. O n8n **não é
dependência** de nenhum deles.

### Para reproduzir a automação

| Requisito | Papel |
|---|---|
| **Node.js** | runtime do n8n |
| **npm / npx** | baixa e executa o n8n |

O n8n **é necessário apenas para reproduzir a automação** descrita aqui. Sem
ele, o agente continua inteiro; o que se perde é esta porta de entrada.

### Ambiente efetivamente comprovado

| Componente | Versão usada na execução registrada |
|---|---|
| Node.js | **24.19.0** |
| npm | **11.17.0** |
| n8n | **2.36.8** |

**Estas são as versões testadas, não versões mínimas.** Nada aqui demonstra o
comportamento em versões anteriores ou posteriores — só se afirma o que foi
observado. A versão do n8n deve permanecer **fixada em `2.36.8`** ao reproduzir:
outra versão pode exigir `typeVersion` diferente nos nós.

### O que NÃO é necessário

- **não é necessária conta no n8n Cloud**;
- **não é necessário Docker**;
- **não é necessário serviço externo** de nenhum tipo;
- **não é necessária instalação global**: `npx` baixa e executa a versão fixada
  `n8n@2.36.8` sob demanda, sem `npm install -g`.

## Como reproduzir

São **três terminais**:

| Terminal | O que roda | Estado |
|---|---|---|
| **1** | a aplicação (`uvicorn`) | fica em primeiro plano |
| **2** | os três comandos do n8n, em sequência | o `start` fica em primeiro plano |
| **3** | a chamada ao webhook | pontual |

Regras que valem para as duas sequências abaixo:

- os **três comandos do n8n** — `import:workflow`, `publish:workflow` e `start` —
  usam **o mesmo `N8N_USER_FOLDER`**, definido **no terminal 2**, e podem ser
  executados sequencialmente ali mesmo;
- `N8N_USER_FOLDER` aponta para um **diretório dedicado, fora do repositório**.
  Nenhum dado da instância local entra na árvore versionável;
- o endereço da aplicação é **`127.0.0.1:8000`**, e **não** `localhost` — o
  motivo está em *Ponto mais provável de falha*;
- nenhuma sequência depende de variável configurada em outro terminal;
- **todos os comandos com caminho relativo** — inclusive o executável do `.venv`
  e o `--input` do `import:workflow` — devem ser executados **a partir da raiz do
  repositório**;
- a aplicação sobe pelo **interpretador do `.venv`**, indicado explicitamente:
  assim a sequência não depende de o ambiente virtual estar ativado. No Windows,
  em uma nova janela do PowerShell sem o ambiente virtual ativado, chamar
  `python` diretamente pode acionar o Python global, que não possui as
  dependências instaladas no `.venv`.

### A. Windows PowerShell

**Terminal 1 — aplicação:**

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — n8n.** Os três comandos, na ordem, no mesmo terminal:

```powershell
$env:N8N_USER_FOLDER = "C:\dados-n8n-javalog"
npx.cmd n8n@2.36.8 import:workflow --input=docs/low-code/javalog-agent-n8n.json
npx.cmd n8n@2.36.8 publish:workflow --id=javalog-agent-lowcode
npx.cmd n8n@2.36.8 start
```

O `start` **fica em primeiro plano** — deixe o terminal 2 ocupado.

**Terminal 3 — chamada ao webhook:**

```powershell
$corpo = '{"file_path":"examples/logs/application-clean.log"}'
$corpo | curl.exe -X POST http://127.0.0.1:5678/webhook/javalog-agent `
  -H "Content-Type: application/json" `
  --data-binary "@-"
```

Use **`curl.exe`**, e não `curl`: no Windows PowerShell, `curl` é apelido de
`Invoke-WebRequest`, que tem outra sintaxe e não aceita estes argumentos.

### B. Linux ou macOS

**Terminal 1 — aplicação:**

```bash
./.venv/bin/python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

No Git Bash sobre Windows, substitua `./.venv/bin/python` por
`./.venv/Scripts/python.exe`; os demais comandos Bash permanecem iguais.

**Terminal 2 — n8n.** Os três comandos, na ordem, no mesmo terminal:

```bash
export N8N_USER_FOLDER="$HOME/dados-n8n-javalog"
npx n8n@2.36.8 import:workflow --input=docs/low-code/javalog-agent-n8n.json
npx n8n@2.36.8 publish:workflow --id=javalog-agent-lowcode
npx n8n@2.36.8 start
```

O `start` **fica em primeiro plano** — deixe o terminal 2 ocupado.

**Terminal 3 — chamada ao webhook:**

```bash
curl -X POST http://127.0.0.1:5678/webhook/javalog-agent \
  -H "Content-Type: application/json" \
  -d '{"file_path":"examples/logs/application-clean.log"}'
```

### Por que a ordem importa

`import:workflow` grava o fluxo no banco da instância; `publish:workflow` o
ativa; só então `start` sobe o servidor **já com o webhook registrado**. A
própria ferramenta avisa: *"Changes will not take effect if n8n is running"*.
Publicar com o servidor no ar exige reiniciá-lo.

### Ponto mais provável de falha

O nó **HTTP Request** aponta para `http://127.0.0.1:8000/api/v1/analyze`. O
endereço é **IPv4 explícito**, e não `localhost`, por um motivo medido nesta
etapa: em Node 24, `localhost` resolve primeiro para `::1`, e uma API ligada
apenas a `127.0.0.1` recusa a conexão. Rodando o n8n em contêiner, `127.0.0.1`
passa a ser o próprio contêiner, e o endereço precisa ser trocado — por exemplo,
`http://host.docker.internal:8000/api/v1/analyze`.

## Execução local real

| Campo | Valor |
|---|---|
| Ferramenta | **n8n 2.36.8** |
| Forma de inicialização | `npx n8n@2.36.8 start`, instância local, sem conta e sem serviço externo |
| Dados da instância | fora da árvore do projeto, em `N8N_USER_FOLDER` dedicado |
| API | `python -m uvicorn src.api:app --host 127.0.0.1 --port 8000` |
| URL local do webhook | `http://127.0.0.1:5678/webhook/javalog-agent` |
| Data e hora | **2026-08-28**, entre `08:52:11Z` e `08:52:24Z` |

### Execução 2 — caminho feliz

| Campo | Valor |
|---|---|
| Identificador da execução no n8n | **`2`** |
| Modo | `webhook` |
| Início · fim | `2026-08-28 08:52:11.341` · `2026-08-28 08:52:12.094` |
| Status registrado pelo n8n | **`success`** |
| Payload enviado | `{"file_path":"examples/logs/application-clean.log"}` |
| Código HTTP devolvido pelo webhook | **`200`** |

Sequência dos três nós, com o tempo medido pelo próprio n8n:

```text
Webhook Trigger      status=success    0 ms
HTTP Request         status=success  738 ms
Respond to Webhook   status=success    6 ms
ultimo no executado: Respond to Webhook
```

Trecho não sensível da resposta devolvida pelo webhook:

```json
{
  "status": "success_no_errors",
  "correlation_id": "ec56ecbe-98c2-4385-8cea-3f17a934517d",
  "audit_id": "5bc5c739-a068-48a6-985c-368a9fb5ad5d",
  "diagnostic": {
    "summary": "Nenhum erro relevante encontrado.",
    "probable_cause": "N/A",
    "severity": "low",
    "category": "Clean",
    "diagnostic_mode": "deterministic"
  },
  "requires_human": false
}
```

O recorte histórico omite `report_path`. No contrato público atual, novas
respostas expõem o caminho relativo e portátil `output/<nome>.md`.

### Execução 3 — caminho inválido

| Campo | Valor |
|---|---|
| Identificador da execução no n8n | **`3`** |
| Início · fim | `2026-08-28 08:52:24.215` · `2026-08-28 08:52:24.235` |
| Status registrado pelo n8n | **`success`** |
| Payload enviado | `{"file_path":"../../etc/passwd"}` |
| Código HTTP devolvido pelo webhook | **`200`** |

```json
{
  "status": "error",
  "correlation_id": "c8730fce-45b5-40f1-83a9-c3c293825150",
  "audit_id": "b25fcc98-dd8f-40ef-b591-59b766d2b61a",
  "diagnostic": null,
  "error": "Acesso negado. O arquivo deve estar dentro de examples/logs.",
  "requires_human": false
}
```

**O erro é propagado no corpo, não no código HTTP.** A API responde `400` a esse
pedido, mas o webhook responde `200` com `status: "error"` no corpo. Isso é
consequência de `neverError: true` no nó HTTP Request, e é deliberado: caminho
recusado é uma **resposta válida do domínio**, não uma falha de infraestrutura, e
não deve abortar o fluxo. Falha de infraestrutura continua abortando — foi
exatamente o que aconteceu na primeira tentativa desta etapa.

Quem consome o webhook distingue os dois casos pelo campo `status` do corpo, não
pelo código HTTP.

### Reprodução da sequência documentada

As instruções acima foram executadas **do zero**, num `N8N_USER_FOLDER` novo e
dedicado, para conferir que a sequência publicada funciona como está escrita:

| Campo | Valor |
|---|---|
| Diretório de dados | novo, dedicado, fora do repositório e em outro volume |
| Data e hora | **2026-08-28**, `09:10:56Z` |
| Identificador da execução no n8n | **`1`** — banco novo, contagem reiniciada |
| Status registrado pelo n8n | **`success`** |
| Código HTTP devolvido pelo webhook | **`200`** |
| `correlation_id` devolvido | `c6f4d2ed-29f3-494b-bb11-3f0127537399` |

```text
Webhook Trigger      status=success     1 ms
HTTP Request         status=success  1838 ms
Respond to Webhook   status=success     6 ms
ultimo no executado: Respond to Webhook
```

A chamada custou mais que na primeira rodada — 1838 ms contra 738 ms no nó de
integração — porque a aplicação havia acabado de subir e o grafo ainda não
estava aquecido. O desfecho é o mesmo.

## O que foi comprovado

| Afirmação | Como foi comprovada |
|---|---|
| **O fluxo executa no n8n** | execuções registradas no banco da instância, com identificador, modo `webhook`, início, fim e status |
| **Os três nós executam, na ordem** | `Webhook Trigger → HTTP Request → Respond to Webhook`, todos `success`, com tempos medidos pelo n8n |
| **O nó HTTP chamou a aplicação de verdade** | a resposta traz `correlation_id` e `audit_id` gerados pela execução do agente; a primeira tentativa falhou com `ECONNREFUSED`, prova de que há chamada real de rede |
| **A saída é observável** | o webhook devolveu `200` com o diagnóstico estruturado no corpo |
| **O erro de domínio é propagado** | caminho fora do diretório permitido devolve `status: "error"` com a mensagem literal da aplicação |
| **A sequência documentada funciona** | repetida do zero, em diretório de dados novo, com o mesmo desfecho |
| O arquivo é **JSON válido e importável** | importado pela linha de comando: `Successfully imported 1 workflow` |
| **Nenhuma credencial** no JSON | nenhum nó declara `credentials`; varredura por chaves e por formatos de segredo não encontra ocorrência; `authentication: none` |
| O fluxo **não reimplementa lógica** | nenhum nó de código, função, condicional, filtro ou atribuição; o corpo é encaminhado sem alteração |
| O endpoint chamado **existe e responde** | a suíte extrai o caminho **do próprio JSON** e exercita a API: log limpo → `200`; travessia de diretório → `400` |

Salvo as execuções no n8n, todas as demais afirmações têm verificação
automatizada em `tests/test_n8n_workflow.py`, que roda na suíte e no pipeline.

## O que NÃO foi comprovado

A execução local **não** demonstra:

| Não comprovado | Por quê |
|---|---|
| **Deploy** | não houve publicação em servidor, contêiner ou serviço gerenciado. A instância foi criada por `npx`, usada e descartada |
| **Disponibilidade contínua** | o n8n rodou por poucos minutos, o suficiente para as execuções registradas. Nada aqui demonstra o fluxo ativo ao longo do tempo, sobrevivendo a reinício ou a falha |
| **Funcionamento em outra topologia de rede** | o endereço `127.0.0.1` funciona porque n8n e API rodam na mesma máquina. Em contêiner, em outro host ou atrás de proxy, o endereço precisa mudar |
| **Reprodutibilidade em outra versão** | a evidência é de **n8n 2.36.8** sobre **Node.js 24.19.0**. Versões diferentes podem exigir outro `typeVersion` de nó |

### Limitações da evidência registrada

- os identificadores de execução são **locais da instância** descartada: não
  podem ser reabertos por terceiros;
- o banco da instância **não é versionado**, por decisão — carrega estado
  operacional e nada acrescentaria à revisão do fluxo;
- os `correlation_id` citados pertencem a execuções daquele momento; repetir a
  chamada gera outros.

## Onde vive a lógica

```text
Webhook Trigger  ->  HTTP Request  ->  Respond to Webhook
   recebe            encaminha o        devolve o que a
   a requisicao      corpo intacto      aplicacao respondeu
```

Validação de caminho, leitura confinada do arquivo, extração de eventos,
classificação do erro, política de autonomia, diagnóstico e emissão dos sinais
acontecem **inteiramente na aplicação**. Trocar o n8n por outra ferramenta, ou
remover a automação, não muda nenhum comportamento do agente — o que se perde é
a porta de entrada, não a capacidade.

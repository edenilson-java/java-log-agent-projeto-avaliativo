# Evidência — API, MCP e automação low-code

As três formas de acionar o agente além da CLI, com o resultado real de cada uma.

## API HTTP

Exercitada pela fronteira, sem chave e sem rede externa:

| Requisição | Código | Resultado |
|---|---:|---|
| `GET /health` | `200` | `{"status": "ok", "service": "javalog-agent"}` |
| `POST /api/v1/tools/read-log` — log válido | `200` | conteúdo devolvido; caminho **sem barra invertida**, portátil |
| `POST /api/v1/tools/read-log` — `../../etc/passwd` | `400` | acesso negado |
| `POST /api/v1/analyze` — cenário principal | `200` | `status: success_fallback` |
| `POST /api/v1/analyze` — cenário adversarial | `409` | `status: blocked`, `requires_human: true` |
| `POST /api/v1/analyze` — `file_path` com tipo errado | `422` | recusado no contrato de fronteira, antes do fluxo |

Três coisas que essa tabela demonstra:

**O bloqueio chega ao cliente como conflito, não como erro genérico.** `409` com
`requires_human: true` diz ao consumidor que a recusa exige decisão humana, e não
que a requisição estava malformada.

**O tipo errado nunca alcança o grafo.** `422` vem do contrato Pydantic da
fronteira — a validação acontece antes de qualquer leitura de arquivo.

**O caminho devolvido é portátil.** A saída pública usa separador POSIX, para que
um cliente em outro sistema não receba um caminho que não sabe interpretar.

## Servidor MCP

Local, por stdio, exercitado **atravessando `call_tool`** — o caminho que um
cliente MCP real percorre, e não a chamada direta à função:

```text
tools expostas:      ['read_log']
resources expostos:  0
prompts expostos:    0

call_tool read_log (log válido)         -> status=success
call_tool read_log (../../etc/passwd)   -> status=error · "Acesso negado: o arquivo está fora do diretório…"
call_tool read_log (extensão .pdf)      -> status=error · "Extensão inválida: .pdf. Permitidas: .log e .txt"
call_tool escrever (inexistente)        -> ToolError: Unknown tool: escrever
```

**Uma única capability, read-only.** O servidor MCP não expõe escrita, não expõe
recurso e não chama o modelo. É a superfície mínima que resolve o caso: ler um
log confinado. Qualquer coisa além disso seria autonomia que o projeto não
precisa conceder.

**O confinamento vale igual nas três fronteiras.** A mesma travessia de diretório
é recusada na CLI, na API e no MCP, porque a proteção vive na tool, não na borda.

## Automação low-code

Fluxo n8n de três nós, **executado de verdade** numa instância local:

```text
Webhook Trigger  ->  HTTP Request  ->  Respond to Webhook
```

| Aspecto | Evidência |
|---|---|
| Execução real | n8n **2.36.8**, execuções registradas com identificador, status e tempos por nó |
| Integração | `POST http://127.0.0.1:8000/api/v1/analyze`, corpo encaminhado sem alteração |
| Saída observável | webhook devolveu **`200`** com o diagnóstico estruturado |
| Erro de domínio | caminho inválido devolveu `status: "error"` no corpo, com a mensagem literal da aplicação |
| Credenciais | **nenhuma** no arquivo exportado |
| Lógica | **nenhum** nó reimplementa validação, extração, classificação ou diagnóstico |

O relato completo — versões, comandos, identificadores de execução, sequência dos
nós, o que foi e o que **não** foi comprovado — está em
[`../low-code/reproducao.md`](../low-code/reproducao.md).

## A relação entre as quatro portas

```text
CLI ─┐
API ─┼─> mesmo grafo, mesma lógica, mesmas proteções
MCP ─┘
        ▲
        └── n8n chama a API, como qualquer cliente HTTP
```

Nenhuma das fronteiras reimplementa regra. Remover qualquer uma delas — inclusive
a automação low-code — **não muda o comportamento do agente**; o que se perde é
uma porta de entrada, não uma capacidade.

# README e exemplos versionados

**Tipo:** Prompt de documentação
**Arquivos relacionados:** `README.md` e `examples/results/`
**Objetivo:** documentar instalação, arquitetura, execução, segurança, testes e fornecer exemplos reproduzíveis de entrada e saída.

## Prompt utilizado

Crie a documentação principal do projeto JavaLog Agent.

Requisitos para `README.md`:

- apresentar o objetivo do agente;
- listar as funcionalidades implementadas;
- explicar o fluxo do `StateGraph`;
- mostrar a estrutura principal do repositório;
- informar Python 3.12 e as dependências de `requirements.txt`;
- documentar a criação e ativação do ambiente virtual no PowerShell;
- explicar a configuração opcional de `OPENAI_API_KEY`;
- deixar claro que, sem chave, o agente usa fallback determinístico;
- fornecer comandos reais para executar os três logs versionados;
- informar que relatórios locais são gravados em `output`;
- explicar os estados finais:
  - `success`;
  - `success_fallback`;
  - `success_no_errors`;
  - `error`;
- documentar os limites de segurança:
  - diretório permitido;
  - extensões aceitas;
  - limite de tamanho;
  - bloqueio de path traversal;
  - escrita restrita;
  - ausência de shell e capacidades extras;
- documentar a execução dos testes;
- registrar o resultado real de 26 testes aprovados;
- não afirmar cobertura percentual não medida;
- não inventar recursos ausentes.

Requisitos para `examples/results/`:

- versionar uma saída correspondente a cada log de exemplo;
- manter os relatórios locais de execução em `output` ignorados pelo Git;
- copiar para `examples/results` somente exemplos destinados à documentação;
- preservar UTF-8 e quebras de linha LF;
- deixar explícito que:
  - logs com erros foram executados em modo `fallback`;
  - o log limpo foi executado em modo `deterministic`.

## Exemplos versionados

Entradas:

- `examples/logs/application-clean.log`;
- `examples/logs/bean-creation-error.log`;
- `examples/logs/null-pointer-exception.log`.

Saídas:

- `examples/results/report_application-clean.md`;
- `examples/results/report_bean-creation-error.md`;
- `examples/results/report_null-pointer-exception.md`.

## Validações realizadas

- leitura dos requisitos reais em `requirements.txt`;
- leitura da configuração em `.env.example`;
- confirmação da ajuda real da CLI com `python -m src.main --help`;
- execução dos três logs de exemplo;
- geração dos três relatórios locais;
- cópia dos relatórios para `examples/results`;
- validação de UTF-8 e LF no `README.md`;
- confirmação do resultado real `26 passed`.

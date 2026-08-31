# Apresentação do projeto

**Tipo:** Prompt de documentação visual
**Arquivo relacionado:** `slides/apresentacao.pdf`
**Objetivo:** apresentar o problema, a solução, as ferramentas, a arquitetura, a segurança e a resiliência do JavaLog Agent.

## Prompt utilizado

Crie uma apresentação técnica do projeto JavaLog Agent.

Requisitos:

- gerar exatamente duas páginas;
- usar linguagem direta e adequada para apresentação acadêmica;
- manter coerência com o código implementado;
- não inventar funcionalidades;
- apresentar na primeira página:
  - problema;
  - objetivo do agente;
  - entrada e saída;
  - ferramentas reais integradas;
- apresentar na segunda página:
  - fluxo do StateGraph;
  - decisões condicionais;
  - estado compartilhado;
  - segurança e guardrails;
  - resiliência e fallback;
- informar que a entrada é um arquivo `.log` via CLI;
- informar que a saída é um relatório Markdown;
- mostrar que a leitura é restrita a `examples/logs`;
- mostrar que a escrita é restrita a `output`;
- registrar o bloqueio de path traversal;
- registrar a extração de eventos `ERROR`, `WARN` e exceções Java;
- registrar a validação estruturada com Pydantic;
- registrar que logs limpos não chamam o LLM;
- registrar que o diagnóstico realiza no máximo uma chamada ao LLM;
- registrar o fallback determinístico para chave ausente, falha do LLM ou saída inválida;
- incluir o nome do autor no rodapé;
- manter aparência profissional e boa legibilidade.

## Validações realizadas

- arquivo com cabeçalho PDF válido;
- exatamente duas páginas detectadas;
- tamanho de 7782 bytes;
- SHA-256:
  `8F02000B3D2CAD43DD4040BD31B35F80693A554D66354767588BB35C2B8C94B8`;
- conteúdo visual conferido;
- nome do autor presente no rodapé.

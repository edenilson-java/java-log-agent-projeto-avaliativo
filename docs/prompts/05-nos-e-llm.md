# Nós do agente, diagnóstico com LLM e fallback

**Tipo:** Prompt de implementação do bloco
**Arquivo relacionado:** `src/nodes.py`
**Objetivo:** implementar os nós do agente com estado compartilhado, diagnóstico estruturado, injeção explícita do LLM e fallback determinístico.

## Prompt utilizado

Implemente `src/nodes.py` para o projeto JavaLog Agent em Python 3.12.

Requisitos:

- usar `AgentState` como contrato de estado compartilhado;
- cada nó deve devolver somente a atualização do estado;
- validar a entrada antes de qualquer leitura;
- produzir resposta de erro sem chamar ferramenta ou LLM quando a entrada for inválida;
- ler o log somente pela ferramenta segura `read_log_file`;
- extrair exceções, eventos e evidências com limite de contexto;
- classificar logs de modo determinístico;
- gerar resultado específico para logs sem erros relevantes;
- realizar no máximo uma chamada ao LLM para o diagnóstico;
- usar `DiagnosticReport` como schema de saída estruturada;
- criar o nó de diagnóstico por meio de `make_diagnosticar(llm)`;
- permitir injeção explícita de FakeLLM nos testes;
- não usar atributos especiais de objetos de teste no código de produção;
- não usar `hasattr(llm, "should_fail")` ou mecanismo equivalente;
- exigir `OPENAI_API_KEY` somente quando nenhum LLM for injetado;
- usar `ChatOpenAI` com temperatura zero;
- tratar falhas da LLM como estado observável;
- validar novamente o diagnóstico antes da saída;
- gerar fallback determinístico quando a LLM falhar ou produzir saída inválida;
- limpar o erro residual após fallback bem-sucedido;
- não incluir o campo `diagnostic` quando não houver diagnóstico;
- escrever o relatório somente pela ferramenta segura `write_diagnostic_report`;
- não executar shell, rede direta, escrita irrestrita ou capacidades extras.

A implementação deve fornecer:

- `validar_entrada`;
- `gerar_resposta_erro`;
- `ler_log`;
- `extrair_eventos`;
- `classificar_log`;
- `gerar_resultado_sem_erros`;
- `make_diagnosticar`;
- `validar_saida`;
- `tratar_saida_invalida`;
- `escrever_relatorio`.

## Validações realizadas

- compilação com `py_compile`;
- verificação de UTF-8 e quebras de linha LF;
- confirmação da ausência de `hasattr`;
- falha controlada quando a chave da OpenAI não está configurada;
- resposta de entrada inválida sem `diagnostic`;
- fallback com status de sucesso;
- limpeza do campo `error` após fallback.

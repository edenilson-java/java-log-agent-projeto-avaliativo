# Grafo LangGraph e interface de linha de comando

**Tipo:** Prompt de implementação do bloco
**Arquivos relacionados:** `src/graph.py` e `src/main.py`
**Objetivo:** montar o fluxo completo do agente em LangGraph e disponibilizar sua execução por linha de comando.

## Prompt utilizado

Implemente `src/graph.py` e `src/main.py` para o projeto JavaLog Agent em Python 3.12.

Requisitos para `src/graph.py`:

- usar `StateGraph(AgentState)`;
- usar as constantes `START` e `END`;
- não usar `set_entry_point`;
- registrar os dez nós implementados em `src/nodes.py`;
- injetar o LLM no nó de diagnóstico por meio de `create_graph(llm=None)`;
- manter quatro roteamentos condicionais:
  - após validação da entrada;
  - após leitura do log;
  - após classificação;
  - após validação da saída;
- encaminhar entrada inválida diretamente para resposta de erro;
- encerrar o fluxo de erro sem chamar ferramentas adicionais ou LLM;
- encaminhar log limpo para diagnóstico determinístico;
- encaminhar log com erros para diagnóstico com LLM;
- usar fallback determinístico quando a saída do LLM for inválida;
- escrever o relatório antes do encerramento dos fluxos bem-sucedidos;
- retornar o grafo compilado;
- não adicionar loops, memória persistente ou capacidades extras.

Requisitos para `src/main.py`:

- carregar variáveis de ambiente com `load_dotenv`;
- receber o caminho do log como argumento obrigatório;
- criar o grafo com `create_graph`;
- iniciar o estado somente com `file_path`;
- executar o agente com `invoke`;
- apresentar status final, caminho do relatório e modo de diagnóstico;
- retornar código de saída zero para sucesso;
- retornar código de saída um para erro de entrada ou falha crítica;
- não conter lógica de negócio duplicada dos nós.

## Validações realizadas

- compilação de `graph.py` e `main.py` com `py_compile`;
- verificação de UTF-8 e quebras de linha LF;
- confirmação do uso de `START`;
- confirmação da ausência de `set_entry_point`;
- execução de log com erro sem chave de API, resultando em `success_fallback`;
- execução de log limpo, resultando em `success_no_errors`;
- bloqueio de path traversal, resultando em `error` e código de saída um;
- geração dos relatórios dentro do diretório `output`.

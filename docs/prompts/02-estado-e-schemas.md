# 02 - Estado e Schemas

**Tipo:** Especificação de implementação do bloco

## Objetivo

Definir o estado compartilhado do agente e o contrato Pydantic usado para validar diagnósticos estruturados.

## Arquivos

- `src/__init__.py`
- `src/state.py`
- `src/schemas.py`

## Estado compartilhado

`AgentState` deve ser um `TypedDict` parcial capaz de transportar:

- caminho e conteúdo do log;
- eventos e exceções extraídos;
- categoria e evidências;
- diagnóstico estruturado;
- caminho do relatório;
- status, erro e erros de validação.

## Schema de diagnóstico

`DiagnosticReport` deve validar:

- resumo;
- causa provável;
- severidade;
- categoria;
- exceção principal opcional;
- evidências;
- recomendações;
- modo de diagnóstico.

Os campos textuais obrigatórios não podem aceitar strings vazias ou compostas somente por espaços.

## Restrições

- Não implementar ferramentas, nós, grafo, CLI ou testes automatizados neste bloco.
- Não realizar chamadas a LLM.
- Manter todos os arquivos em UTF-8 sem mojibake.
- Manter consistência entre o número deste arquivo e seu título interno.

## Critérios de aceite

- `AgentState` e `DiagnosticReport` podem ser importados.
- Um diagnóstico válido é aceito.
- Um campo textual vazio é rejeitado pelo Pydantic.
- A palavra `execução` está corretamente codificada em `src/state.py`.
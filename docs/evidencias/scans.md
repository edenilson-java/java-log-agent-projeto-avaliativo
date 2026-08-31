# Evidência — varredura de segredos e recursos proibidos

O que é procurado, como é procurado, e por que o resultado tem valor.

## Resultado

```text
======================================================================
VARREDURA DE SEGREDOS E RECURSOS PROIBIDOS
======================================================================

Arquivos versionados inspecionados: 80

[1] Segredos no conteudo dos arquivos versionados
  -> 0 ocorrencia(s) de segredo

[2] Artefatos locais versionados por engano
  -> verificado

[3] Notebook como formato principal e relatorios gerados
  -> verificado

[4] Arquivos de construcao dentro do repositorio
  -> verificado

======================================================================
RESULTADO: NADA ENCONTRADO — zero ocorrencias
```

A varredura é executada **antes de cada integração**, não só no fim.

## O que é procurado

| Frente | O que reprova |
|---|---|
| **Segredos** | chaves de provedor, tokens de repositório, esquema portador, atribuições do tipo `api_key = <valor longo>` |
| **Artefatos locais** | `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/` versionados |
| **Formato e saída gerada** | notebook como formato principal; relatórios `output/*.md` e sinais `output/*.jsonl` versionados |
| **Arquivos de construção** | documentos de trabalho interno dentro do repositório |

## Por que "zero" aqui significa alguma coisa

Um scanner quebrado também imprime zero. A diferença é o **controle negativo**:
uma isca sintética é plantada, a varredura precisa **acusá-la**, e só então a
isca é removida e a varredura repetida.

```text
com a isca plantada    ->  1 ocorrencia acusada     (exit 1)
apos remover a isca    ->  NADA ENCONTRADO          (exit 0)
```

Sem esse par, "zero ocorrências" seria indistinguível de um comando que não olhou
para lugar nenhum.

## Dois cuidados que o desenho precisou ter

**O scanner contém os padrões que procura.** Se ele varresse a si mesmo,
acusaria as próprias expressões regulares. A busca exclui o arquivo do scanner —
e essa exclusão é a única, com a lista de isenções **vazia** no restante.

**Padrão de detecção não é valor real.** `src/security.py` contém expressões que
descrevem formatos de credencial; são regras, não segredos. Pelo mesmo motivo,
os valores sintéticos usados nos testes são **montados em tempo de execução**,
por concatenação, e nunca escritos como literal completo — um literal de aparência
credível num arquivo de teste é exatamente o que uma varredura deve acusar.

## Lista de isenções

**Vazia.** Nenhum arquivo do produto está fora da varredura.

Houve uma versão inicial com três isenções, duas delas indefensáveis —
`.env.example`, que é justamente o arquivo com maior chance de receber uma chave
real por descuido, e `src/security.py`, que é código do produto. A correção está
registrada como ciclo em [`../evolucao-mini-projeto.md`](../evolucao-mini-projeto.md).

## Proteção de credencial em camadas

A varredura é a última linha, não a única:

| Camada | Onde |
|---|---|
| `.env` no `.gitignore` desde o primeiro commit | `.gitignore` |
| Chave só por variável de ambiente, encapsulada em `SecretStr` | `src/config.py` |
| Redação de dez formatos antes de prompt, arquivo, sinal ou resposta | `src/security.py` |
| Workflow de CI sem `secrets.` e sem variável de chave | `.github/workflows/ci.yml` |
| Fluxo low-code exportado sem `credentials` | `docs/low-code/javalog-agent-n8n.json` |
| Varredura executável antes de cada integração | esta evidência |

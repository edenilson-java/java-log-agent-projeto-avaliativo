# Revisão de código assistida por IA

Análise do diff real entre a baseline transportada do mini-projeto e o estado
evoluído do projeto. O diff analisado está versionado em
[`diff-baseline-real.patch`](diff-baseline-real.patch) — é um patch aplicável,
não um resumo em prosa.

## O que foi analisado

| Item | Valor |
|---|---|
| Base | commit do transporte da baseline |
| Alvo | estado evoluído após seis etapas técnicas |
| Escopo | `src/` e `tests/` |
| Arquivos no diff | 19 |
| Tamanho | 4 540 inserções, 64 exclusões |
| Aplicabilidade | `git apply --check` em código zero, sobre uma árvore limpa na base |
| Fidelidade | aplicado numa árvore de trabalho separada, reproduz os 19 arquivos idênticos ao estado evoluído |

## Método

A leitura do diff foi conduzida por três perguntas, na ordem:

1. **algum campo é publicado sem ter sido medido?** — campos que aparecem em
   saída pública mas nunca são escritos por nenhum produtor;
2. **algum contrato herdado foi alterado sem registro?** — literais, nomes de
   nó, assinaturas e mensagens da baseline;
3. **alguma verificação afirma mais do que executa?** — asserções que passariam
   mesmo se o comportamento sob teste fosse removido.

As duas últimas perguntas não produziram achado nesta revisão: os literais
herdados seguem conferidos caractere a caractere por teste versionado, e a
suíte é medida por campanhas de mutação a cada etapa. A primeira produziu um
achado real, descrito abaixo.

## Achado 1 — o log de aplicação publicava um código HTTP que nunca foi medido

**Severidade:** média. Não quebra execução, mas insere dado falso na trilha de
investigação, que é justamente o artefato consultado quando algo dá errado.

### Localização

| Onde | O quê |
|---|---|
| `src/observability.py`, tupla `CAMPOS_DE_DETALHE` | publicava `http_status` no campo livre do log de aplicação |
| `src/state.py`, linha `http_status: int` | campo declarado no estado |
| `src/graph.py`, `CAMPOS_POR_EXECUCAO` | zerado a cada execução, com `"http_status": 0` |

### Problema encontrado

`http_status` é **declarado**, **zerado** e **publicado** — mas **nenhum
produtor o escreve**. A busca por escrita no diff devolve uma única ocorrência,
que é a própria inicialização com zero:

```text
src/graph.py:64          "http_status": 0,      <- inicialização
src/observability.py:46  "http_status",         <- publicação no sinal
src/state.py:102         http_status: int       <- declaração
```

O motivo é estrutural, não um esquecimento pontual: o código HTTP é decidido
em `src/api.py`, a partir do `status` do domínio, **depois** que o grafo
retorna — e o sinal é emitido **dentro** do grafo, no ponto único de término.
Quando a linha é gravada, o código HTTP ainda não existe.

O efeito é que toda linha do log de aplicação afirmava `http_status: 0`. Zero
não é um código HTTP válido: quem investiga lê um valor que contradiz a
resposta efetivamente devolvida.

**Reprodução pela fronteira HTTP, antes da correção:**

```text
entrada                                  HTTP real   no sinal
examples/logs/application-clean.log            200          0   <-- diverge
examples/logs/adversarial-prompt-injection     409          0   <-- diverge
```

### Trecho anterior

```python
# Campos do estado que compõem o campo livre do log de aplicação.
CAMPOS_DE_DETALHE = (
    "category",
    "thread_id",
    "request_source",
    "current_step",
    "llm_attempts",
    "requires_human",
    "redacted",
    "security_flags",
    "node_history",
    "report_path",
    "http_status",
)
```

### Diff da correção

```diff
-# Campos do estado que compõem o campo livre do log de aplicação.
+# Só entram campos que a execução produziu: o código HTTP é decidido na
+# fronteira, depois desta emissão.
 CAMPOS_DE_DETALHE = (
     "category",
     "thread_id",
     "request_source",
     "current_step",
     "llm_attempts",
     "requires_human",
     "redacted",
     "security_flags",
     "node_history",
     "report_path",
-    "http_status",
 )
```

### Por que essa correção, e não outra

Três alternativas foram consideradas:

| Alternativa | Descartada porque |
|---|---|
| Preencher `http_status` no grafo | acoplaria o núcleo ao protocolo HTTP; a CLI e o servidor MCP não têm código HTTP |
| Emitir um segundo par de sinais na fronteira HTTP | quebraria o invariante de **uma linha por execução em cada sinal**, que é o que torna a correlação legível |
| Remover o campo do estado | o campo integra o contrato de estado do projeto e continua disponível para a fronteira que quiser usá-lo |

A correção adotada mantém o campo no estado e retira apenas a **afirmação**
que não podia ser sustentada. Omitir é melhor do que publicar zero: a ausência
é honesta, o zero é falso.

### Teste refinado

Teste de **integração**, acrescentado em `tests/test_api.py`: exercita a API
por HTTP, confere o código devolvido e depois lê a linha gravada no sinal.

```python
@pytest.mark.parametrize(
    ("caminho", "codigo_esperado"),
    [
        (LOG_LIMPO, 200),
        ("examples/logs/adversarial-prompt-injection.log", 409),
    ],
    ids=["200", "409"],
)
def test_sinal_nao_publica_status_http(
    client, sinais_isolados, caminho, codigo_esperado
):
    resposta = client.post("/api/v1/analyze", json={"file_path": caminho})
    assert resposta.status_code == codigo_esperado

    eventos, auditoria = sinais_isolados()
    assert len(eventos) == 1

    assert "http_status" not in eventos[0]["details"]
    assert "http_status" not in auditoria[0]
```

O teste percorre os dois desfechos que produzem códigos diferentes — `200` no
log limpo e `409` no cenário bloqueado — para que a asserção não dependa de um
único caminho.

### Resultado executado

**Antes da correção**, com o teste já escrito:

```text
FAILED tests/test_api.py::test_sinal_nao_publica_status_http[200]
FAILED tests/test_api.py::test_sinal_nao_publica_status_http[409]
AssertionError: assert 'http_status' not in {'category': 'Unknown',
  'current_step': 1, 'http_status': 0, 'llm_attempts': 0, ...}
2 failed, 1 passed
```

**Depois da correção:**

```text
3 passed
```

**Reprodução pela fronteira HTTP, depois:**

```text
entrada                                  HTTP real   no sinal
examples/logs/application-clean.log            200  <ausente>
examples/logs/adversarial-prompt-injection     409  <ausente>
casos em que o sinal contradiz a resposta HTTP: 0
```

**Suíte completa e verificadores, sem chave e com a rede externa bloqueada:**

```text
pytest -q                345 passed      (342 -> 345)
ruff check .             All checks passed!
compileall               exit 0
verificador da E06       172 verificações, exit 0
verificadores E05..E01   158 / 100 / 97 / 62 / 38, todos exit 0
```

## Achados descartados

Registrados por transparência: foram levantados na leitura e **não** viraram
correção, com o motivo.

| Observação | Por que não virou correção |
|---|---|
| `gerar_resultado_sem_erros` grava `report_path` com um nome de arquivo, e `escrever_relatorio` o sobrescreve com o caminho real logo em seguida | comportamento herdado da baseline, sem efeito observável: o valor final é sempre o do nó seguinte. Alterá-lo mexeria em contrato herdado sem ganho |
| O relatório em `output/` guarda o caminho absoluto da máquina | é o retorno da ferramenta de escrita e já aparece na resposta pública desde etapas anteriores; mudar exigiria alterar contrato já validado |
| `parallel_findings` acumula entre execuções da mesma thread | o reducer mescla por origem, e as duas origens são reescritas a cada execução que chega ao fan-in; o caso residual não é alcançável por rota que leia o campo |

## Origem da análise

O diff analisado, o achado, a correção, os testes e todas as saídas acima foram
produzidos **neste** repositório, sobre **este** código. Nenhum texto,
resultado ou evidência foi copiado de qualquer outro projeto.

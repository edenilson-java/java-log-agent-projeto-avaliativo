# Evidência — o pacote entregue

O que está no repositório, o que deliberadamente não está, e como o fluxo de
versionamento foi conduzido.

## Contagem

**80 arquivos versionados.** Distribuição:

| Local | Arquivos | Conteúdo |
|---|---:|---|
| `src/` | 15 | o agente |
| `tests/` | 15 | a suíte |
| `docs/` | 33 | arquitetura, evidências, QA, DevOps, low-code, segurança e os dez prompts |
| `examples/` | 9 | logs de exemplo, série simulada e relatórios de referência |
| raiz | 5 | `README.md`, `requirements.txt`, `.env.example`, `.gitignore`, `.gitattributes` |
| `.github/` | 1 | o workflow de CI |
| `slides/` | 1 | a apresentação do miniprojeto, registro histórico |
| `output/` | 1 | apenas o `.gitkeep` — o diretório entra versionado e **vazio** |

## O que NÃO está no repositório, por decisão

| Ausente | Motivo |
|---|---|
| `.env` | credencial nunca entra no versionamento — ignorado desde o primeiro commit |
| `.venv/`, `__pycache__/`, `.pytest_cache/` | artefatos locais, reconstruídos por quem clona |
| `output/*.md`, `output/*.jsonl` | relatórios e sinais são **gerados em execução**; versioná-los seria confundir saída com fonte |
| documentos de trabalho interno | pertencem à construção, não ao produto avaliado |
| dados da instância local do n8n | banco, cache e configuração da ferramenta viveram fora da árvore |

Cada uma dessas ausências é **verificada por varredura executável**, não apenas
declarada. Ver [`scans.md`](scans.md).

## Fluxo de versionamento

| Aspecto | Estado |
|---|---|
| Branches remotas | **11** — `main`, `develop` e nove branches de etapa, **todas preservadas** |
| Pull Requests para `develop` | **10**, todos mesclados com **merge commit real** |
| Merge com squash ou rebase | **nenhum** — todo merge tem dois pais |
| Commits na `develop` | 22, entre commits autorais de etapa e merge commits |
| `main` | intocada desde o commit de bootstrap, aguardando o Pull Request final de integração |

A `main` guardar apenas o bootstrap **é o estado planejado**: a integração final
acontece por um único Pull Request `develop → main`, ao fim de tudo. Enquanto
isso, `develop` é a linha integrada.

## Integração contínua

O workflow roda em toda branch e em todo Pull Request destinado a `develop` ou
`main`, com três etapas:

```text
Lint       ruff check src tests
Testes     pytest -q --disable-warnings
Compile    python -m compileall -q src
```

Sem segredo, sem passo de publicação, com permissão restrita a leitura de
conteúdo. Os runs reais e seus logs estão em
[`../devops/logs-ci.md`](../devops/logs-ci.md).

## Como conferir tudo isso a partir de um clone

**Windows PowerShell:**

```powershell
git clone --branch develop https://github.com/edenilson-java/java-log-agent-projeto-avaliativo.git
cd java-log-agent-projeto-avaliativo

(git ls-files).Count                 # 80
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q                # 413 passed
.\.venv\Scripts\python.exe -m src.main examples/logs/null-pointer-exception.log
.\.venv\Scripts\python.exe -m src.main examples/logs/adversarial-prompt-injection.log
```

**Linux ou macOS:**

```bash
git clone --branch develop https://github.com/edenilson-java/java-log-agent-projeto-avaliativo.git
cd java-log-agent-projeto-avaliativo

git ls-files | wc -l                 # 80
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q      # 413 passed
./.venv/bin/python -m src.main examples/logs/null-pointer-exception.log
./.venv/bin/python -m src.main examples/logs/adversarial-prompt-injection.log
```

O interpretador do ambiente virtual é invocado **pelo caminho**, e não pelo
`python` do sistema: criar o `.venv` não o ativa, e sem ativação o `python` da
linha seguinte ainda é o global — a instalação iria para o lugar errado e a
suite rodaria contra outras dependências. Chamar pelo caminho dispensa a
ativação e vale igual nos dois sistemas.

O **segundo cenário termina com código de saída `1`**, e isso é o esperado: é a
recusa da entrada adversarial sendo propagada a quem chamou.

O `--branch develop` é **explícito e necessário**: sem ele, o clone traz a branch
padrão `main`, que ainda está no commit de bootstrap.

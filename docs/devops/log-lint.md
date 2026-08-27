# Log da etapa de lint

Saída bruta da primeira das duas etapas do pipeline analisadas neste projeto.
É o mesmo comando que o workflow executa no passo **Lint**, rodado localmente
sobre a árvore de trabalho candidata ao versionamento.

## Como foi produzido

| Campo | Valor |
|---|---|
| Comando | `ruff check src tests` |
| Ferramenta | ruff 0.16.4 |
| Interpretador | Python 3.12.10 |
| Ambiente | local, sem chave de modelo e sem acesso a rede externa |
| Código de saída | `0` |

## Saída bruta

```text
All checks passed!
```

## O que a saída significa

`ruff` percorre `src/` e `tests/` e imprime uma linha por violação. A ausência
de linhas de diagnóstico, somada ao código de saída `0`, é o resultado: nenhuma
regra do conjunto ativo foi violada em nenhum dos arquivos analisados.

O que essa saída **não** afirma:

- não diz que o código está correto — lint verifica forma, não comportamento;
- não substitui a etapa de testes, que roda em seguida e é o que exercita o
  comportamento;
- não cobre arquivos fora de `src/` e `tests/`.

## Escopo analisado

| Diretório | Arquivos Python |
|---|---:|
| `src/` | 15 |
| `tests/` | 13 |

O escopo do comando é deliberadamente `src tests`, e não a raiz: os arquivos de
configuração e os dados de exemplo não são código do produto, e incluí-los
transformaria o sinal do lint em ruído.

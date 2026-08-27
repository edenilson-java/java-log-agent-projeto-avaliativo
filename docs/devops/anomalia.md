# Anomalia detectada e estimativa de risco

## Natureza dos dados — declaração obrigatória

**A série de execuções analisada neste documento é SIMULADA e documentada.**

Ela não foi coletada de nenhum pipeline real, de nenhum sistema em produção e de
nenhuma execução do GitHub Actions. Foi definida pelo projeto **antes** de
qualquer teste existir, e seus valores são referência congelada.

A rotulagem não vive apenas nesta prosa:

| Onde | Como a série é declarada simulada |
|---|---|
| `examples/devops/pipeline_runs.json` | campo obrigatório `"simulated": true` e campo `purpose` descrevendo a finalidade |
| `src/devops.py` | `load_pipeline_runs` **levanta erro** e recusa calcular se o rótulo não estiver presente e verdadeiro |
| `tests/test_devops.py` | testes exigem a recusa da série sem rótulo e da série rotulada como não simulada |
| este documento | esta seção |

A validação em código impede que uma série sem a declaração obrigatória seja
processada por engano. Ela valida o metadado declarado, não a procedência: não
distingue dados simulados de dados reais falsamente rotulados. A procedência
desta série específica é documentada nos campos `purpose` e `source` e neste
documento.

## A série

| id | fase | duração (s) | status |
|---|---|---:|---|
| `baseline-1` | baseline | 12 | passed |
| `baseline-2` | baseline | 14 | passed |
| `baseline-3` | baseline | 15 | failed |
| `recent-1` | recent | 30 | passed |
| `recent-2` | recent | 35 | failed |

## As métricas

Saída real de `python -m src.devops`:

```json
{
  "baseline_average": 13.67,
  "failure_rate_percent": 40.0,
  "growth_percent": 137.8,
  "recent_average": 32.5,
  "risk_score_percent": 64.0
}
```

Como cada número sai da série:

```text
baseline_average_exact = (12 + 14 + 15) / 3 = 41 / 3 = 13.666666...
baseline_average       = round(41 / 3, 2)            = 13.67
recent_average         = (30 + 35) / 2   = 65 / 2    = 32.5

growth_percent         = (32.5 - 41/3) / (41/3) * 100
                       = 137.804878...
                       = 137.8   apos o arredondamento a duas casas

failure_rate_percent   = 2 falhas / 5 execucoes * 100 = 40.0
normalized_growth      = min(100, max(0, 137.804878...))  = 100
risk_score_percent     = 0.4 * 100 + 0.6 * 40             = 64.0
```

**O crescimento é calculado sobre a média integral, não sobre a arredondada.**
A distinção não é decorativa: usar a média já arredondada como divisor daria
**137.75**, e não 137.8. O arredondamento a duas casas é aplicado apenas na
apresentação de cada métrica, **depois** do cálculo — arredondar antes
propagaria o erro para todas as grandezas derivadas dela.

## A anomalia

**A anomalia detectada é o crescimento de 137,8% na duração média das execuções
recentes em relação à baseline, combinado a uma taxa de falha de 40%.**

### Evidências utilizadas

| Evidência | Valor | Por que sustenta a conclusão |
|---|---|---|
| Duração média da baseline | 13,67 s | ponto de comparação, três execuções |
| Duração média recente | 32,5 s | **mais que o dobro** da baseline |
| Crescimento | 137,8% | acima do teto de saturação de 100 do modelo de risco |
| Taxa de falha | 40% | 2 das 5 execuções terminaram em `failed` |
| Distribuição das falhas | `baseline-3` e `recent-2` | a falha **não** é exclusiva da fase recente |

### Por que é anomalia, e não variação normal

Nenhum dos dois sinais isolados bastaria:

- **crescimento sozinho** poderia ser explicado por trabalho novo legítimo — uma
  suíte que cresceu, uma etapa acrescentada ao pipeline. Duração maior não é,
  por si, defeito;
- **taxa de falha sozinha** em 40% é alta, mas a série mostra falha também na
  baseline: não é um regime novo, é um regime que já era instável.

O que caracteriza a anomalia é a **conjunção**: a duração mais que dobrou **e** a
instabilidade permaneceu. Um pipeline que fica mais lento enquanto continua
falhando consome mais tempo para entregar a mesma incerteza — o custo por
execução sobe sem que a confiança suba junto.

### Conclusão justificada

**A estimativa de risco é de 64,0%**, e ela é dominada pelo termo de crescimento:

```text
0.4 * 100 (crescimento, saturado)  = 40.0
0.6 *  40 (taxa de falha)          = 24.0
                                     ----
                                     64.0
```

O crescimento de 137,8% **satura** em 100 antes da ponderação. Isso é uma decisão
do modelo, não um efeito colateral: sem o teto, uma única execução patológica —
uma duração de 600 segundos, por exemplo — levaria o risco a valores sem
significado e apagaria a contribuição da taxa de falha. Com o teto, o modelo diz
o que pretende dizer: *o crescimento já está no pior patamar que este indicador
reconhece*, e o que ainda diferencia um cenário de outro é a taxa de falha.

A leitura operacional é: **o risco é alto e a causa provável está na duração, não
na taxa de falha**. A taxa de falha é anterior ao problema — já existia na
baseline. A duração é o que mudou. Uma investigação que começasse pelas falhas
gastaria esforço num sintoma antigo; a mudança de regime está no tempo de
execução.

### O que esta conclusão não afirma

- **não identifica a causa** do crescimento; a série registra duração e status,
  não o que aconteceu dentro de cada execução;
- **não projeta** o comportamento futuro; são cinco pontos, e cinco pontos não
  sustentam tendência estatística — sustentam comparação entre dois blocos;
- **não vale para nenhum pipeline real**, porque a série é simulada. O que é
  real aqui é o **método**: a detecção, a ponderação e o limite declarado do que
  o número significa.

# Decisões Técnicas (ADRs curtos)

Registro cronológico de decisões metodológicas, técnicas e de arquitetura.

Formato:

```text
## ADR-NNN — Título curto
**Data:** YYYY-MM-DD
**Status:** proposto | aceito | substituído
**Contexto:** o que motivou a decisão
**Decisão:** o que foi decidido
**Consequências:** trade-offs e impactos
```

---

## ADR-001 — Adoção do padrão WAT (Workflow + Agents + Tools)

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** O projeto envolve múltiplas etapas com naturezas distintas (engenharia de dados, estatística, análise socioeconômica, redação institucional). Operar tudo em um único agente generalista resultaria em prompts longos, conflitos de responsabilidade e dificuldade de manutenção.

**Decisão:** Adotar arquitetura WAT em três camadas:

- **Workflow** (slash commands em `.claude/commands/`) orquestra a execução das 4 etapas da minuta.
- **Agents** (`.claude/agents/`) — quatro subagentes especializados, um por etapa.
- **Tools** (`src/`) — funções Python idempotentes e testáveis.

**Consequências:**

- (+) Separação clara de responsabilidades; cada agente carrega só o contexto relevante.
- (+) Reproduzibilidade fora do agente — o pipeline Python pode rodar via `python -m src.ingest.pnadc`.
- (−) Custo inicial de setup maior; exige disciplina para manter agentes magros.

---

## ADR-002 — Stack Python (pandas + pyarrow + matplotlib/plotly)

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** Microdados IBGE são tradicionalmente analisados em R (pacote `survey`, `PNADcIBGE`). Python é mais comum no time do projeto e permite integração natural com Claude Code e Jupyter.

**Decisão:** Python 3.11+ com pandas, pyarrow (parquet), `samplics` para análise amostral com pesos, matplotlib + plotly para visualização, WeasyPrint + python-pptx para entregáveis.

**Consequências:**

- (+) Ecossistema único para todo o pipeline.
- (+) `samplics` cobre estimadores com desenho complexo (UPA, estratos, pesos calibrados).
- (−) Menos exemplos prontos para PNADC do que em R; talvez precise prototipar parser do layout fixo.

---

## ADR-003 — Armazenamento local em `data/` com raw/interim/processed

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** Microdados do Censo somam vários GB. Cliente prefere setup local sem dependência de cloud.

**Decisão:** Convenção:

- `data/raw/` — bruto baixado (gitignore, regenerável por download)
- `data/interim/` — parquet intermediário (gitignore, regenerável)
- `data/processed/` — base final por etapa (gitignore, mas com `.meta.json` versionado seria possível em iteração futura)

**Consequências:**

- (+) Simples, portátil entre máquinas.
- (−) Cada novo dev refaz downloads. Aceitável dado o tamanho do time.

---

## ADR-004 — Microdados obrigatórios; tabulações prontas só para validação

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** Existe a opção de consumir tabulações já publicadas (SIDRA, séries históricas, tabelas auxiliares IBGE), o que aceleraria parte das estimativas. No entanto, isso comprometeria a flexibilidade dos recortes (renda ≤ R$ 40 mil, intersecções não publicadas por UF/sexo/CNAE), o controle metodológico do desenho amostral e a credibilidade técnica do estudo.

**Decisão:** Toda estimativa do projeto é derivada de **cálculo próprio sobre microdados** (PNADC, Censo, dump CNPJ para MEI). Tabulações prontas são permitidas **apenas como referência cruzada de validação** — para checar se nossos números batem com publicações oficiais em recortes equivalentes. Cada validação cruzada deve ser registrada neste documento, identificando "nosso número" vs "referência externa".

**Consequências:**

- (+) Flexibilidade total nos recortes específicos do projeto.
- (+) Controle pleno sobre pesos, estratos, decisões de filtro e tratamento de missings.
- (+) Credibilidade do entregável FGV NPII para a ABEVD.
- (−) Mais trabalho de engenharia de dados (parsers de layout fixo, downloads pesados).
- (−) Maior espaço em disco e tempo de processamento.

---

(Próximas decisões a registrar pelos agentes ao longo da execução.)

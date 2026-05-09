# Nano-empreendedores no Brasil — Estimativa e Caracterização

Estudo técnico para a **ABEVD** (Associação Brasileira das Empresas de Venda Direta), conduzido sob a coordenação do **FGV NPII**, com objetivo de **estimar o universo de nano-empreendedores no Brasil** — trabalhadores por conta própria com renda anual ≤ R$ 40 mil — e **caracterizar seu perfil socioeconômico em todos os estados da federação**.

> Documento de referência: [`minuta/minuta-tecnica.pdf`](minuta/minuta-tecnica.pdf) — minuta técnica, setembro de 2025.

---

## Sumário

- [Objetivos](#objetivos)
- [Fontes de dados](#fontes-de-dados)
- [Etapas do trabalho](#etapas-do-trabalho)
- [Arquitetura WAT do agente](#arquitetura-wat-do-agente)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Como executar](#como-executar)
- [Produtos finais](#produtos-finais)

---

## Objetivos

1. Estimar o **número de nano-empreendedores** por UF e região.
2. Caracterizar o **perfil socioeconômico** desse grupo (sexo, idade, cor/raça, escolaridade, setor, renda).
3. Distinguir o **segmento formalizado** (com CNPJ MEI) do **informal**.
4. Subsidiar o **planejamento estratégico da ABEVD** para expansão da rede de consultoras de venda direta e planejamento tributário de longo prazo.

## Fontes de dados

> **Princípio inegociável:** todas as estimativas do projeto são derivadas de **cálculo próprio sobre microdados**. Tabulações prontas (SIDRA, séries publicadas) não são usadas como insumo — apenas como referência cruzada para validar nossos cálculos. Veja [ADR-004](docs/decisoes-tecnicas.md).

| Fonte | Órgão | Uso no projeto |
| --- | --- | --- |
| **PNAD Contínua** (microdados trimestrais) | IBGE | Fonte primária para estimar conta-própria com renda ≤ R$ 40 mil/ano, com expansão amostral |
| **Censo Demográfico** (microdados) | IBGE | Referência estrutural em nível municipal, robustez das estimativas |
| **Cadastro Nacional MEI** (dump CNPJ Dados Abertos) | Receita Federal / Sebrae | Identificar formalização (CNPJ MEI ativo), atividade CNAE, localização |

Detalhes de download, padronização e dicionário em [`docs/metodologia.md`](docs/metodologia.md) e [`docs/dicionario-dados.md`](docs/dicionario-dados.md).

## Etapas do trabalho

Conforme cronograma da minuta (3 meses):

1. **Preparação e formatação das bases** — extração, padronização, dicionário próprio.
2. **Estimativa do universo** — recorte de renda, expansão amostral, cruzamento com MEI.
3. **Caracterização socioeconômica** — perfis demográficos, econômicos e territoriais.
4. **Relatório técnico final** — documento PDF + sumário executivo + apresentação executiva.

## Arquitetura WAT do agente

O projeto é operado por um agente Claude Code organizado em três camadas:

```text
┌──────────────────────────────────────────────────────────┐
│  WORKFLOW   slash commands em .claude/commands/          │
│             orquestram a sequência das 4 etapas          │
├──────────────────────────────────────────────────────────┤
│  AGENTS     subagentes especializados em .claude/agents/ │
│             cada um conduz uma etapa metodológica        │
├──────────────────────────────────────────────────────────┤
│  TOOLS      funções Python em src/                       │
│             ingestão, transformação, análise, viz, report│
└──────────────────────────────────────────────────────────┘
```

| Camada | Responsabilidade | Onde fica |
| --- | --- | --- |
| Workflow | Orquestrar a execução conversacional das etapas | [.claude/commands/](.claude/commands/) |
| Agents | Conhecimento metodológico + decisão sobre quais tools chamar | [.claude/agents/](.claude/agents/) |
| Tools | Operações determinísticas e reproduzíveis sobre dados | [src/](src/) |

Subagentes definidos:

- [`data-engineer`](.claude/agents/data-engineer.md) — Etapa 1
- [`statistician`](.claude/agents/statistician.md) — Etapa 2
- [`socioeconomic-analyst`](.claude/agents/socioeconomic-analyst.md) — Etapa 3
- [`report-writer`](.claude/agents/report-writer.md) — Etapa 4

Slash commands de workflow:

- `/etapa-1-preparar-bases`
- `/etapa-2-estimar-universo`
- `/etapa-3-caracterizar`
- `/etapa-4-relatorio`
- `/pipeline-completo` — encadeia as 4 etapas

## Estrutura de pastas

```text
nano-empreendedores/
├── .claude/
│   ├── agents/              # subagentes WAT
│   ├── commands/            # slash commands de workflow
│   └── settings.local.json  # permissões locais
├── src/                     # tools Python
│   ├── ingest/              # download e parse das fontes oficiais
│   ├── transform/           # harmonização CNAE/ocupação, recortes
│   ├── analysis/            # expansão amostral, perfis, comparações
│   ├── viz/                 # gráficos e tabelas
│   └── report/              # construção do relatório final
├── data/
│   ├── raw/                 # microdados brutos baixados (não versionado)
│   ├── interim/             # parquet intermediário
│   └── processed/           # bases finais por etapa
├── docs/                    # metodologia, dicionário, decisões técnicas
├── outputs/
│   ├── tabelas/             # CSV/XLSX
│   ├── graficos/            # PNG/SVG/HTML
│   └── relatorios/          # PDF, PPTX
├── notebooks/               # exploração e prototipagem
├── tests/
├── minuta/                  # minuta técnica de referência
├── pyproject.toml
└── README.md
```

## Como executar

### Pré-requisitos

- Python 3.11+
- ~30 GB de espaço em disco para microdados do Censo

### Setup

```powershell
# instalar dependências
pip install -e .

# baixar bases (etapa 1)
python -m src.ingest.pnadc --trimestre 2024Q4
python -m src.ingest.censo --tabela domicilios
python -m src.ingest.mei --uf todos
```

Ou, dentro do Claude Code, rodar `/etapa-1-preparar-bases` e o agente conduz a etapa.

## Produtos finais

Conforme minuta:

- **Relatório Técnico Final** em PDF editável
- **Sumário Executivo** com insights estratégicos
- **Apresentação Executiva** em PowerPoint para reuniões de diretoria
- Tabelas e gráficos em [outputs/](outputs/)

---

**Coordenação técnica:** Fernando Blumenschein (FGV NPII)
**Cliente:** ABEVD

# Guia para o agente Claude — Projeto Nano-empreendedores

## O que é este projeto

Estudo técnico para a **ABEVD** (FGV NPII), descrito na [minuta técnica](minuta/minuta-tecnica.pdf). Estima e caracteriza nano-empreendedores no Brasil (conta-própria com renda anual ≤ R$ 40 mil) por UF, em 4 etapas, terminando em relatório técnico + sumário executivo + apresentação executiva.

## Arquitetura: padrão WAT

| Camada | Pasta | Responsabilidade |
| --- | --- | --- |
| **W**orkflow | [.claude/commands/](.claude/commands/) | Slash commands que orquestram as 4 etapas |
| **A**gents | [.claude/agents/](.claude/agents/) | Subagentes especializados — 1 por etapa |
| **T**ools | [src/](src/) | Funções Python idempotentes (ingestão, análise, viz, relatório) |

### Quando usar o quê

- Usuário quer **executar uma etapa** → invoque o slash command apropriado (`/etapa-N-...`).
- Slash command é **fino**: sua função é decidir o subagente certo e passar contexto.
- Subagente carrega o **conhecimento metodológico** da etapa e chama tools Python.
- Tools Python são **determinísticas** — sem prompts, sem decisões, só código testável.

### Como decidir onde adicionar nova capacidade

| Pergunta | Onde adicionar |
| --- | --- |
| Operação determinística sobre dados? | Tool Python em `src/...` |
| Conhecimento metodológico de uma etapa? | Agent em `.claude/agents/...` |
| Sequência conversacional de execução? | Command em `.claude/commands/...` |

## Princípios não-negociáveis

1. **Microdados são a única fonte primária.** Toda estimativa é derivada de cálculo próprio sobre microdados (PNADC, Censo, dump CNPJ para MEI). **Tabulações prontas (SIDRA, tabelas auxiliares, séries publicadas) NÃO podem ser usadas como insumo** — apenas como referência cruzada para validar nossos cálculos, com a comparação registrada em [docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md). Veja ADR-004.
2. **Pesos amostrais sempre.** PNADC e Censo são amostras complexas. Estatística sem peso é inválida.
3. **Não invente números.** Toda afirmação numérica em relatório deve ter referência à tabela/cálculo de origem.
4. **Documente decisões metodológicas** em [docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md) (formato ADR).
5. **Atualize o dicionário** ([docs/dicionario-dados.md](docs/dicionario-dados.md)) sempre que harmonizar uma nova variável.
6. **Não comite microdados brutos** — eles ficam em `data/raw/` e estão no `.gitignore`.
7. **Microdados pesados** — Censo pode ter vários GB. Sempre ofereça baixar UF a UF se aplicável.

## Convenções de código

- Python 3.11+, type hints obrigatórios em assinaturas públicas.
- Caminhos sempre via `src.paths` — não hardcode strings.
- Persistência em **parquet** (pyarrow), CSV apenas para outputs revisáveis.
- Encoding `utf-8-sig` em CSVs para Excel BR ler corretamente.
- Logs em português técnico; mensagens de erro úteis (com path, contagem, hash).

## Pontos abertos no momento (maio/2026)

- [ ] Confirmar com cliente: renda bruta vs líquida, inclui transferências, idade mínima
- [ ] Definir trimestre alvo da PNADC para a primeira rodada
- [ ] Verificar disponibilidade dos microdados do Censo 2022
- [ ] Snapshot de referência do dump CNPJ MEI a usar

Veja [docs/metodologia.md](docs/metodologia.md) seção 1 para detalhes.

## Comandos úteis

```powershell
# instalar
pip install -e .[dev]

# rodar etapas isoladamente (sem agente)
python -m src.ingest.pnadc --trimestre 2024Q4
python -m src.ingest.censo --uf todos --tabela pessoas
python -m src.ingest.mei

# testes
pytest

# lint
ruff check .
```

## Onde olhar primeiro em uma sessão nova

1. [README.md](README.md) — visão geral
2. [minuta/minuta-tecnica.pdf](minuta/minuta-tecnica.pdf) — escopo contratual
3. [docs/metodologia.md](docs/metodologia.md) — estado da metodologia
4. [docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md) — decisões já tomadas
5. `outputs/` — entregáveis já gerados (se houver)

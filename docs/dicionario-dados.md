# Dicionário de Dados — Projeto Nano-empreendedores

Vocabulário interno do projeto. Atualizado pelo agente `data-engineer` ao final da Etapa 1.

## Convenções

- Nomes em **snake_case**, sem acentos.
- Tipos: `categoria`, `int`, `float`, `bool`, `data`, `string`.
- Toda variável aqui deve ter origem rastreável em pelo menos uma fonte (PNADC, Censo, MEI).
- Codificações categóricas usam strings semânticas (`"conta_propria"`), não códigos numéricos das fontes.

## Variáveis harmonizadas

Carregadas no parquet `data/processed/PNADC_<trim>.parquet` pelo agente
`data-engineer` (Etapa 1, PNADC). Censo e MEI ainda pendentes.

| Nome interno | Tipo | Origem PNADC | Origem Censo | Origem MEI | Descrição | Observações |
|--------------|------|--------------|--------------|------------|-----------|-------------|
| `uf`         | categoria | UF (cód. IBGE 2 díg.) → sigla | V0001 | UF | Sigla da UF (AC, AL, ..., TO, DF) | 27 valores. Mapeamento aplicado em `_uf_codigo_para_sigla` |
| `municipio_ibge` | int | (não disponível em PNADC) | V0002 | MUNICIPIO | Código IBGE do município | 7 dígitos. **PENDENTE** Censo/MEI |
| `sexo` | categoria | V2007 (1=M, 2=F) | V0601 | — | "masculino" \| "feminino" | |
| `idade_anos` | Int16 | V2009 | V6036 | — | Idade em anos completos | |
| `cor_raca` | categoria | V2010 | V0606 | — | "branca" \| "preta" \| "parda" \| "amarela" \| "indigena" \| "ignorada" | |
| `escolaridade` | categoria | VD3004 | V6400 | — | "sem_instrucao" \| "fundamental" \| "medio" \| "superior" | Códigos PNADC 1–7 colapsados |
| `posicao_ocupacao` | categoria | VD4009 | V6920+ | — | "conta_propria" \| "empregado" \| "empregador" \| "domestico" \| "outro" | NaN para não-ocupados |
| `renda_mensal_brl` | float | VD4019 | V6531 | — | Rendimento mensal habitual de todos os trabalhos, em R$ correntes | Deflação opcional |
| `renda_anual_brl` | float | derivada (`mensal × 12`) | derivada | — | `renda_mensal_brl × 12` | |
| `cnae_secao` | string | V40132 (1 letra A-U, devolvida pelo IBGE) | V6471 → seção | CNAE_FISCAL → seção | Seção CNAE Domiciliar 2.0 | PNADC já entrega seção; não exige tabela de-para |
| `cnae_classe` | string | V4013 (5 díg., CNAE Domiciliar 2.0) | V6471 | CNAE_FISCAL | CNAE 5 dígitos | Para integrar com MEI (CNAE 2.3) será necessária tabela de-para — ver pendência em `harmonize_cnae` |
| `peso_amostral` | float | V1028 (peso COM calibração) | peso_pessoa | (n/a) | Peso para expansão. **Essencial — não descartar** | |
| `upa` | Int64 | UPA | (n/a) | (n/a) | Unidade Primária de Amostragem (PNADC) — **necessário para variância** | |
| `estrato` | Int64 | Estrato | (n/a) | (n/a) | Estrato amostral (PNADC) — **necessário para variância** | |
| `ano` | Int16 | Ano | — | — | Ano de referência | |
| `trimestre` | Int8 | Trimestre | — | — | Trimestre de referência (1–4) | |
| `id_pessoa` | string | UPA+V1008+V1014+V2003 | — | — | Chave única de pessoa | |
| `id_domicilio` | string | UPA+V1008+V1014 | — | — | Chave única de domicílio | |
| `is_nano_empreendedor` | bool | derivada (`filters.py`) | derivada | (n/a) | Atende à definição operacional | Calculada na Etapa 2 |
| `mei_ativo` | bool | (n/a) | (n/a) | SITUACAO_CADASTRAL | MEI ativo na data de referência | **PENDENTE** Etapa 1 — MEI |

## Tabelas de codificação

### `cor_raca`
Implementado em `src/transform/harmonize.py::harmonize_cor_raca`.

| Código PNADC (V2010) | Código Censo (V0606) | Valor harmonizado |
|---|---|---|
| 1 | 1 | branca |
| 2 | 2 | preta |
| 3 | 4 | amarela |
| 4 | 3 | parda |
| 5 | 5 | indigena |
| 9 | 9 | ignorada |

### `escolaridade` (PNADC VD3004 → vocab interno)
Implementado em `src/transform/harmonize.py::harmonize_escolaridade`.

| Código VD3004 | Significado oficial IBGE | Valor harmonizado |
|---|---|---|
| 1 | Sem instrução e menos de 1 ano de estudo | sem_instrucao |
| 2 | Fundamental incompleto | fundamental |
| 3 | Fundamental completo | fundamental |
| 4 | Médio incompleto | medio |
| 5 | Médio completo | medio |
| 6 | Superior incompleto | superior |
| 7 | Superior completo | superior |

### `posicao_ocupacao` (PNADC VD4009 → vocab interno)
Implementado em `src/transform/harmonize.py::harmonize_posicao_ocupacao`.

| Código VD4009 | Significado oficial IBGE | Valor harmonizado |
|---|---|---|
| 01 | Empregado privado com carteira | empregado |
| 02 | Empregado privado sem carteira | empregado |
| 03 | Doméstico com carteira | domestico |
| 04 | Doméstico sem carteira | domestico |
| 05 | Empregado público com carteira | empregado |
| 06 | Militar e estatutário | empregado |
| 07 | Empregado público sem carteira | empregado |
| 08 | Empregador | empregador |
| 09 | **Conta-própria** | **conta_propria** |
| 10 | Trabalhador familiar auxiliar | outro |

### `cnae_secao` (PNADC V40132)
**Não requer mapeamento** — o IBGE entrega diretamente a seção CNAE Domiciliar
2.0 como letra (A–U) na variável V40132.

(Tabelas Censo e MEI a serem preenchidas nas iterações seguintes da Etapa 1.)

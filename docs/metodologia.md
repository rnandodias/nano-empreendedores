# Metodologia

> Documento vivo. Atualizado por cada agente ao final de sua etapa.

## 1. Definição operacional de Nano-empreendedor

**Nano-empreendedor** = pessoa ocupada classificada como **trabalhador por conta própria**, com **rendimento anual ≤ R$ 40.000** (proveniente de todos os trabalhos).

| Parâmetro | Valor default | Fonte da decisão |
|-----------|---------------|------------------|
| Posição na ocupação | Conta própria (PNADC `VD4009` / equivalente Censo) | Minuta técnica, seção 2 |
| Teto de renda anual | R$ 40.000 | Minuta técnica, seção 1 |
| Período de referência da renda | Mensal habitual × 12 | A confirmar com cliente |
| Tipo de renda | Bruta, apenas do trabalho | A confirmar com cliente |
| Idade mínima | 14 anos (PNADC) | Padrão IBGE |

**Pontos abertos** (documentar decisão final aqui após confirmação):
- [ ] Renda bruta ou líquida?
- [ ] Inclui rendimentos não-trabalho (aposentadoria, transferências)?
- [ ] Considerar apenas pessoas com 18+ ou seguir o padrão PNADC (14+)?
- [ ] Atualização monetária do teto (R$ 40 mil de qual ano-base)?

## 2. Fontes de dados

### 2.1 PNAD Contínua (IBGE) — fonte primária

- **URL:** https://www.ibge.gov.br/estatisticas/sociais/trabalho/9171-pesquisa-nacional-por-amostra-de-domicilios-continua-mensal.html
- **FTP:** `ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/`
- **Granularidade:** trimestral, representativa em nível de UF
- **Variáveis-chave:** `UF`, `V2007` (sexo), `V2009` (idade), `V2010` (cor/raça), `VD3004` (escolaridade), `VD4002` (cond. ocupação), `VD4009` (posição na ocupação), `VD4019` (renda mensal habitual de todos os trabalhos), `V4010` (CNAE Domiciliar), `V1028` (peso), `UPA`, `Estrato`
- **Desenho amostral:** complexo (estratificado, conglomerado por UPA, com pesos calibrados)
- **Trimestre alvo do estudo:** *a definir* (sugestão: usar último trimestre fechado e validar com 4 trimestres anteriores para sazonalidade)

### 2.2 Censo Demográfico (IBGE) — referência estrutural

- **Edição:** 2022 (microdados em divulgação faseada — verificar disponibilidade da amostra na data de execução)
- **Granularidade:** municipal
- **Uso:** robustez das estimativas e desagregação subestadual quando necessária

### 2.3 Cadastro Nacional MEI (Receita Federal / Sebrae)

- **URL:** https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/dados-publicos-cnpj
- **Variáveis-chave:** CNPJ, situação cadastral, data de início, CNAE principal, UF, município, opção pelo Simples/MEI
- **Limitação:** não há ligação direta por CPF com PNADC/Censo. Cruzamento é **agregado por UF × CNAE × estrato demográfico**.
- **Atenção:** o teto MEI (~R$ 81.000/ano até 2024) é maior que o teto nano-empreendedor (R$ 40.000). Apenas uma fração dos MEI registrados é nano.

## 3. Etapa 1 — Preparação e formatação

### 3.1 PNAD Contínua trimestral — execução em 2026-05-09

- **Trimestre solicitado:** 2026Q1
- **Trimestre efetivamente baixado:** **2025Q4** (fallback automático — 2026Q1 ainda não publicado pelo IBGE; divulgação trimestral esperada para meados de mai/2026)
- **URL de origem:** `https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2025/PNADC_042025.zip`
- **Tamanho do bruto:** 222.550.359 bytes (~223 MB)
- **SHA-256 do bruto:** `bc1fa6d44948b0601b6b8f3cf6692e79d743d2b01e1e8b600b34030976b361d9`
- **Dicionário/input usado:** `Dicionario_e_input_20221031.zip` (input SAS oficial PNADC, layout fixo de 4000 colunas, do qual extraímos posições, larguras e tipos das 37 variáveis selecionadas)
- **Encoding:** Latin-1 (cp1252) — declarado explicitamente no `pd.read_fwf`

**Saídas geradas:**

| Camada | Arquivo | Tamanho |
|---|---|---|
| `data/raw/pnadc/` | `PNADC_042025.zip` (+ `.meta.json`) | 222,6 MB |
| `data/raw/pnadc/` | `Dicionario_e_input_20221031.zip` + `input_PNADC_trimestral.sas` + `dicionario_PNADC_microdados_trimestral.xls` | 0,4 MB |
| `data/interim/` | `PNADC_042025.parquet` (37 colunas, todas as observações) | 11,9 MB |
| `data/processed/` | `PNADC_042025.parquet` (17 colunas harmonizadas) + `.meta.json` | 8,7 MB |

**Sanity checks (PNADC_042025 — 2025Q4):**

| Métrica | Valor |
|---|---|
| Registros (pessoas) | 498.494 |
| Soma dos pesos calibrados (V1028) | 213.130.549 (≈ população do Brasil) |
| Pessoas ocupadas (qualquer posição) | 224.981 (45,1%) |
| Conta-própria (VD4009 = 09) | 61.363 (12,3% da amostra; 27,3% dos ocupados) |
| População conta-própria expandida | 26.108.918 |
| Pessoas com renda mensal habitual > 0 | 220.419 (44,2%) |
| Renda mensal habitual média (conta-própria, ponderada) | R$ 3.118,33 |
| % conta-própria com renda anual ≤ R$ 40 mil | 77,8% (definição preliminar de nano-empreendedor) |

Os números batem com publicações oficiais da PNADC trimestral (~26 M conta-próprias no país), validando o pipeline.

**Decisões de harmonização aplicadas:**

- `cor_raca` — mapeamento V2010 (5 códigos numéricos + 9) → vocabulário interno de 6 rótulos.
- `escolaridade` — VD3004 (códigos 1–7) colapsado em `sem_instrucao | fundamental | medio | superior`.
- `posicao_ocupacao` — VD4009 (códigos 01–10) colapsado em `conta_propria | empregado | empregador | domestico | outro`. Não-ocupados ficam como `NaN`.
- `cnae_secao` — usada diretamente V40132 (seção CNAE Domiciliar 2.0 já entregue como letra A–U pelo IBGE).
- `uf` — convertida do código IBGE 2 dígitos para sigla.
- **Preservados** na base processada: `peso_amostral` (V1028), `upa`, `estrato`, `id_pessoa`, `id_domicilio`, `ano`, `trimestre` — necessários para Etapa 2 (estimadores com desenho complexo).

### 3.2 Censo Demográfico — adiado pelo IBGE; estudo segue sem ele (ver ADR-007)

**Status em 2026-05-09:** Os **microdados da Amostra do Censo Demográfico 2022** ainda **não foram publicados** pelo IBGE. A divulgação estava prevista para 04/12/2025 e foi adiada sem nova data definida — motivo oficial: "adequação aos padrões de disponibilização em formato compatível com a legislação vigente sobre proteção de dados e alinhado às boas práticas internacionais atuais das estatísticas oficiais" ([nota oficial IBGE](https://www.ibge.gov.br/novo-portal-erramos/45278-adiamento-das-divulgacoes-censo-demografico-2022-microdados-da-amostra-e-censo-demografico-2022-areas-de-ponderacao.html)).

**O que está publicado** (insuficiente para nosso recorte):

- Resultados do Universo (perguntas básicas — sexo, idade, cor/raça, situação domicílio) — **não tem** posição na ocupação, rendimento ou CNAE
- Agregados por setor censitário (já tabulados) — viola ADR-004 (microdados only)

**Decisão (ver ADR-007):** Pular Censo nesta iteração. PNADC sozinha é estatisticamente representativa em nível UF (objetivo central da minuta). Quando IBGE publicar a Amostra, retomamos para enriquecer com análise municipal.

### 3.3 Cadastro MEI — execução em 2026-05-09

**Snapshot processado:** Dados Abertos CNPJ da Receita Federal, mês de referência **2026-04**.

**Endpoint utilizado** (validado, ver ADR-006):

```text
WebDAV público — Nextcloud RFB
https://arquivos.receitafederal.gov.br/public.php/webdav/2026-04/<arquivo>.zip
Basic Auth: user="YggdBLfdninEJX9" (share token)  password=""
```

**Arquivos baixados** (5,47 GB no total, hashes SHA-256 em `data/raw/mei/2026-04/*.meta.json`):

| Arquivo | Tamanho | Uso |
| --- | --- | --- |
| `Simples.zip` | 291 MB | Filtro `opcao_mei = 'S'` E `data_exclusao_mei` vazia |
| `Estabelecimentos0..9.zip` | 5,18 GB | Cruzamento por `cnpj_basico`, `identificador_matriz_filial = '1'` (matriz) |
| `Cnaes.zip` | 22 KB | Tabela auxiliar de descrição CNAE |
| `Municipios.zip` | 41 KB | Tabela auxiliar (de-para RFB → IBGE pendente) |

`Empresas*.zip` **não foram baixados** — não necessários para os recortes da Etapa 2 (UF × CNAE × estrato). Decisão registrada em ADR-006.

**Estratégia em 4 passos** (implementada em `src/ingest/mei.py`):

1. Lê `Simples.zip` em memória → filtra `opcao_mei == 'S'` E `data_exclusao_mei == '0'/vazia` → conjunto de `cnpj_basico` MEI vigentes.
2. Lê os 10× `Estabelecimentos*.zip` em chunks (`pd.read_csv` chunked) → mantém apenas `identificador_matriz_filial = '1'` (matriz) E `cnpj_basico` no conjunto MEI.
3. Calcula `cnpj_completo` (14 dígitos) e a coluna derivada `mei_ativo = (situacao_cadastral == '02')`.
4. Deriva `cnae_principal_secao` (letra A–U) a partir da divisão CNAE (2 primeiros dígitos do `cnae_fiscal_principal`).

**Resultado:** `data/processed/mei_ativos.parquet` — 303 MB.

**Sanity checks** (registrados em `data/processed/mei_ativos.meta.json`):

- 48.097.045 linhas no Simples (universo Simples Nacional)
- 16.791.885 linhas com `opcao_mei = 'S'`
- 16.788.816 linhas com MEI vigente (não excluído)
- 70.864.002 linhas no Estabelecimentos (Brasil completo)
- 16.788.816 matrizes MEI vigentes — bate com a contagem do Simples ✓
- **13.274.159 MEI ATIVOS** (situação cadastral `'02'`)
- 3.494.157 inaptos (`'04'`), 18.328 suspensos (`'03'`), 2.132 baixados (`'08'`)

**Top 5 UFs por MEI ativo:**

| UF | MEI ativos | % do total |
| --- | --- | --- |
| SP | 3.760.305 | 28,3% |
| MG | 1.497.547 | 11,3% |
| RJ | 1.275.727 | 9,6% |
| PR | 925.897 | 7,0% |
| RS | 839.262 | 6,3% |

**Top 6 seções CNAE** (relevante para o recorte ABEVD — venda direta, comércio, serviços pessoais):

| Seção | Descrição | MEI ativos | % |
| --- | --- | --- | --- |
| G | Comércio; reparação de veículos | 3.085.819 | 23,3% |
| H | Transporte, armazenagem e correio | 1.774.947 | 13,4% |
| **S** | **Outras atividades de serviços** (cabeleireiro, estética, etc.) | **1.480.909** | **11,2%** |
| C | Indústrias de transformação | 1.264.963 | 9,5% |
| I | Alojamento e alimentação | 1.185.293 | 8,9% |
| F | Construção | 1.148.453 | 8,6% |

A combinação **G + S** (comércio + serviços pessoais) cobre **34,5% dos MEI ativos** — público naturalmente alinhado ao modelo de venda direta da ABEVD.

**Pendências documentadas** (não bloqueiam Etapa 2):

- `municipio_codigo_ibge` ainda vazio — só temos `municipio_codigo_rfb` (TOM, 4 dígitos). De-para RFB→IBGE será implementado se a Etapa 3 exigir granularidade municipal.
- Harmonização CNAE 2.0 ↔ 2.3 entre PNADC e MEI — ainda como TODO em `src/transform/harmonize.py::harmonize_cnae`. Para a Etapa 2, agregação por seção (A–U) é estável entre as versões.

## 4. Etapa 2 — Estimativa do universo (executada em 2026-05-09)

### 4.1 Pareamento temporal PNADC × MEI

Pareamento canônico para a série 2025 (estoque MEI no fim do trimestre vs amostra PNADC do trimestre):

| Período | PNADC (trimestre) | MEI (snapshot fim do trimestre) |
| --- | --- | --- |
| 2025T1 | Jan-Mar | 2025-03 |
| 2025T2 | Abr-Jun | 2025-06 |
| 2025T3 | Jul-Set | 2025-09 |
| 2025T4 | Out-Dez | 2025-12 |

### 4.2 Expansão amostral (Taylor / samplics)

- **Software:** `samplics 0.4.55` (Python) — `TaylorEstimator` com `param=PopParam.total`
- **Pesos:** `V1028` (calibrado)
- **Estratos:** `Estrato`
- **PSU:** `UPA`
- **Tratamento de estratos com 1 UPA:** `single_psu=SinglePSUEst.certainty` (ver ADR-008)
- **Domínio:** `UF` (estimativas por estado)
- **Confiança:** IC 95% (alpha=0.05)
- **Implementação:** `src/analysis/universe_estimator.py::estimar_universo_uf`

### 4.3 Cruzamento PNADC × MEI

Cruzamento agregado por UF (não por CPF — MEI é dado administrativo):

- `mei_ativos_total`: contagem direta do cadastro MEI (não amostra)
- `taxa_formalizacao_aprox = min(mei_ativos / total_nano_estimado, 1.0)`
- `informais_aprox = total_nano_estimado − min(mei_ativos, total_nano_estimado)`

**Limitação importante:** o teto MEI vigente (R$ 81 mil/ano até 2024) é maior que o teto nano (R$ 40 mil). Logo, **nem todo MEI é nano-empreendedor** — uma fração dos MEI tem renda > R$ 40 mil/ano. Resultado: a `taxa_formalizacao_aprox` é uma cota superior; o número real de "MEIs com renda nano" é menor. Em SP, por exemplo, a taxa de 98% provavelmente reflete essa contaminação. Refinamento possível em iteração futura: estimar a fração de MEI com renda > R$ 40 mil a partir da própria PNADC (conta-própria com renda > 40k formalizado / total conta-própria > 40k).

### 4.4 Resultados (série 2025)

Tabela completa em `outputs/tabelas/etapa2/nano_serie_temporal.csv`. Resumo Brasil:

| Período | Total nano estimado | CV médio (%) |
| --- | --- | --- |
| 2025T1 | 19.405.869 | ~4 |
| 2025T2 | 19.452.967 | ~4 |
| 2025T3 | 19.434.042 | ~4 |
| 2025T4 | 19.155.732 | ~4 |

**Achado principal:** universo nano-empreendedor estável em ~19,4 milhões durante 2025; MEI ativos cresceram ~10-15% no mesmo período (de 13,02M no fim de T4) — evidência de **migração informal → formal em curso**.

## 5. Etapa 3 — Caracterização socioeconômica (executada em 2026-05-09)

Implementação em `src/analysis/profiles.py`. Quatro tabelas em `outputs/tabelas/etapa3/`:

### 5.1 Perfil demográfico

`perfil_demografico.csv` — distribuição ponderada por UF × dimensão × valor, para 4 dimensões: sexo, faixa etária (14-24, 25-49, 50+), cor/raça, escolaridade. 1.513 linhas (4 períodos × 27 UFs × ~14 categorias agregadas).

### 5.2 Perfil econômico

`perfil_economico.csv` — média e mediana ponderadas do `renda_mensal_brl` por UF. 108 linhas (4 períodos × 27 UFs).

### 5.3 Perfil setorial

`perfil_setorial.csv` — distribuição ponderada por seção CNAE (A-U) × UF. ~1.821 linhas. Sobre `cnae_secao`: derivado de `V4013` via tabela divisão→seção (ver ADR-009; `V40132` veio vazia em 2025).

### 5.4 Recorte estratégico ABEVD

`perfil_recorte_abevd.csv` — **mulheres 25-49 anos** atuando em **Comércio (G) ou Serviços pessoais (S)** como nano-empreendedoras. Esse é o público naturalmente alinhado ao modelo de venda direta.

**Achado:** **1,14 milhão de mulheres** no Brasil em 2025T4. Top UFs: SP (247k), MG (148k), RJ (124k), BA (77k), PE (55k), RS (50k), CE (48k), PR (45k), GO (44k), PA (39k). Representa 5-8% do universo nano em cada UF.

## 6. Limitações conhecidas

- **PNADC subestima** algumas categorias informais por dificuldades de captação domiciliar.
- **MEI não é universo** dos formalizados — só captura quem optou pela formalização específica MEI.
- **Censo 2022** ainda em divulgação — verificar versão dos microdados disponível.
- **Heterogeneidade da renda autônoma** — flutua mês a mês; rendimento habitual pode subestimar/sobreestimar.

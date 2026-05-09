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

### 3.2 Censo Demográfico — pendente

A executar em iteração seguinte da Etapa 1.

### 3.3 Cadastro MEI — pendente

A executar em iteração seguinte da Etapa 1. Requer dump CNPJ da Receita Federal e filtro por `OPCAO_MEI`.

## 4. Etapa 2 — Estimativa do universo

### 4.1 Expansão amostral

PNADC requer estimadores de variância que respeitem o desenho complexo. Usar:

- **Pesos:** `V1028` (calibrado)
- **Estratos:** `Estrato`
- **PSU:** `UPA`
- **Software:** `samplics` (Python) ou `survey` (R) — implementação manual deve ser justificada

(Documentar memorial de cálculo após execução.)

### 4.2 Cruzamento PNADC × MEI

(Documentar abordagem após execução.)

## 5. Etapa 3 — Caracterização socioeconômica

(Documentar análises e recortes após execução.)

## 6. Limitações conhecidas

- **PNADC subestima** algumas categorias informais por dificuldades de captação domiciliar.
- **MEI não é universo** dos formalizados — só captura quem optou pela formalização específica MEI.
- **Censo 2022** ainda em divulgação — verificar versão dos microdados disponível.
- **Heterogeneidade da renda autônoma** — flutua mês a mês; rendimento habitual pode subestimar/sobreestimar.

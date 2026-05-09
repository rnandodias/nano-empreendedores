# Dicionário de Dados — Projeto Nano-empreendedores

Vocabulário interno do projeto. Atualizado pelo agente `data-engineer` ao final da Etapa 1.

## Convenções

- Nomes em **snake_case**, sem acentos.
- Tipos: `categoria`, `int`, `float`, `bool`, `data`, `string`.
- Toda variável aqui deve ter origem rastreável em pelo menos uma fonte (PNADC, Censo, MEI).
- Codificações categóricas usam strings semânticas (`"conta_propria"`), não códigos numéricos das fontes.

## Variáveis harmonizadas

Carregadas no parquet `data/processed/PNADC_<trim>.parquet` (PNADC) e
`data/processed/mei_ativos.parquet` (MEI) pelo agente `data-engineer`
(Etapa 1). Censo ainda pendente.

| Nome interno | Tipo | Origem PNADC | Origem Censo | Origem MEI | Descrição | Observações |
|--------------|------|--------------|--------------|------------|-----------|-------------|
| `uf`         | categoria | UF (cód. IBGE 2 díg.) → sigla | V0001 | `uf` (Estabelecimentos col. 20, sigla 2 letras) | Sigla da UF (AC, AL, ..., TO, DF) | 27 valores. PNADC mapeado em `_uf_codigo_para_sigla`; MEI já vem como sigla |
| `municipio_ibge` | int | (não disponível em PNADC) | V0002 | (não resolvido nesta rodada — MEI traz código RFB-TOM 4 díg.) | Código IBGE do município | 7 dígitos. **PENDENTE** Censo. Para MEI ver `municipio_codigo_rfb` (de-para RFB→IBGE em iteração futura) |
| `sexo` | categoria | V2007 (1=M, 2=F) | V0601 | — (cadastro CNPJ não tem sexo do titular) | "masculino" \| "feminino" | |
| `idade_anos` | Int16 | V2009 | V6036 | — | Idade em anos completos | |
| `cor_raca` | categoria | V2010 | V0606 | — | "branca" \| "preta" \| "parda" \| "amarela" \| "indigena" \| "ignorada" | |
| `escolaridade` | categoria | VD3004 | V6400 | — | "sem_instrucao" \| "fundamental" \| "medio" \| "superior" | Códigos PNADC 1–7 colapsados |
| `posicao_ocupacao` | categoria | VD4009 | V6920+ | — (todos os MEI são, por definição, conta-própria formalizado) | "conta_propria" \| "empregado" \| "empregador" \| "domestico" \| "outro" | NaN para não-ocupados |
| `renda_mensal_brl` | float | VD4019 | V6531 | — (cadastro não tem renda; o teto MEI é regulatório, não observado) | Rendimento mensal habitual de todos os trabalhos, em R$ correntes | Deflação opcional |
| `renda_anual_brl` | float | derivada (`mensal × 12`) | derivada | — | `renda_mensal_brl × 12` | |
| `cnae_principal_secao` | categoria | V40132 (1 letra A-U, devolvida pelo IBGE) | V6471 → seção | derivado de `cnae_fiscal_principal` (Estabelecimentos col. 11) via tabela inline divisão→seção em `src/ingest/mei.py::CNAE_DIVISAO_TO_SECAO` | Letra A-U da seção CNAE 2.x | PNADC e MEI usam CNAE 2.x — seção é compatível direta |
| `cnae_principal_classe` | string | V4013 (5 díg., CNAE Domiciliar 2.0) | V6471 | `cnae_fiscal_principal` (Estabelecimentos col. 11; 7 díg., CNAE Fiscal 2.x) | Código CNAE | MEI traz 7 díg. (subclasse), PNADC 5 díg. (classe). Para join no nível classe truncar MEI nos 5 primeiros dígitos. Ver `harmonize_cnae` (pendente) |
| `peso_amostral` | float | V1028 (peso COM calibração) | peso_pessoa | (n/a — cadastro é universo, não amostra) | Peso para expansão. **Essencial — não descartar** | |
| `upa` | Int64 | UPA | (n/a) | (n/a) | Unidade Primária de Amostragem (PNADC) — **necessário para variância** | |
| `estrato` | Int64 | Estrato | (n/a) | (n/a) | Estrato amostral (PNADC) — **necessário para variância** | |
| `ano` | Int16 | Ano | — | — | Ano de referência | |
| `trimestre` | Int8 | Trimestre | — | — | Trimestre de referência (1–4) | |
| `id_pessoa` | string | UPA+V1008+V1014+V2003 | — | — | Chave única de pessoa | |
| `id_domicilio` | string | UPA+V1008+V1014 | — | — | Chave única de domicílio | |
| `is_nano_empreendedor` | bool | derivada (`filters.py`) | derivada | (n/a — definição é renda + posição na ocupação, ambos da PNADC) | Atende à definição operacional | Calculada na Etapa 2 |
| `cnpj_basico` | string | (n/a) | (n/a) | Simples col. 0 / Estabelecimentos col. 0 | 8 primeiros dígitos do CNPJ (raiz da empresa) | Chave de join Simples × Estabelecimentos |
| `cnpj_completo` | string | (n/a) | (n/a) | derivado: `cnpj_basico` + `cnpj_ordem` (Estab col. 1) + `cnpj_dv` (col. 2) | CNPJ 14 dígitos | |
| `municipio_codigo_rfb` | string | (n/a) | (n/a) | Estabelecimentos col. 20 (TOM, 4 dígitos) | Código RFB do município | Tabela de-para RFB→IBGE não aplicada nesta rodada |
| `data_inicio_atividade` | string (AAAAMMDD) | (n/a) | (n/a) | Estabelecimentos col. 10 | Data de início de atividade no CNPJ | Formato `YYYYMMDD` como string |
| `data_opcao_mei` | string (AAAAMMDD) | (n/a) | (n/a) | Simples col. 5 | Data em que o titular optou pelo enquadramento MEI | |
| `data_situacao_cadastral` | string (AAAAMMDD) | (n/a) | (n/a) | Estabelecimentos col. 6 | Data da situação cadastral atual | |
| `situacao_cadastral` | categoria | (n/a) | (n/a) | Estabelecimentos col. 5 | Código RFB (`01`,`02`,`03`,`04`,`08`) — ver tabela abaixo | |
| `mei_ativo` | bool | (n/a) | (n/a) | derivado: `opcao_mei='S'` ∧ `data_exclusao_mei` vazia/`'0'` ∧ `situacao_cadastral='02'` | MEI ativo no snapshot | Já filtramos em `filter_mei` por MEI vigente; flag indica também situação cadastral ativa |

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

### `situacao_cadastral` (MEI / Estabelecimentos RFB col. 5)

Códigos oficiais conforme `cnpj-metadados.pdf` da Receita Federal.

| Código | Significado oficial | Tratamento no projeto |
|---|---|---|
| `01` | Nula | inativo (`mei_ativo=False`) |
| `02` | **Ativa** | **ativo (`mei_ativo=True`)** |
| `03` | Suspensa | inativo |
| `04` | Inapta | inativo |
| `08` | Baixada | inativo |

A flag `mei_ativo` em `data/processed/mei_ativos.parquet` é
`(opcao_mei='S')` ∧ (`data_exclusao_mei` vazia/`'0'`) ∧ (`situacao_cadastral='02'`).
O parquet preserva também as linhas em que o titular é MEI vigente no Simples
mas o estabelecimento (matriz) está em outra situação cadastral, para análise
de ex-ativos / pendências; nesses casos `mei_ativo=False`.

### `cnae_principal_secao` (MEI — derivado de `cnae_fiscal_principal`)

Tabela divisão CNAE 2.x → seção, do IBGE/CONCLA. Implementada inline em
`src/ingest/mei.py::CNAE_DIVISAO_TO_SECAO`.

| Divisão (2 dígitos) | Seção | Descrição abreviada |
|---|---|---|
| 01–03 | A | Agricultura, pecuária, produção florestal, pesca e aquicultura |
| 05–09 | B | Indústrias extrativas |
| 10–33 | C | Indústrias de transformação |
| 35 | D | Eletricidade e gás |
| 36–39 | E | Água, esgoto, gestão de resíduos |
| 41–43 | F | Construção |
| 45–47 | G | Comércio; reparação de veículos |
| 49–53 | H | Transporte, armazenagem e correio |
| 55–56 | I | Alojamento e alimentação |
| 58–63 | J | Informação e comunicação |
| 64–66 | K | Atividades financeiras e de seguros |
| 68 | L | Atividades imobiliárias |
| 69–75 | M | Atividades profissionais, científicas e técnicas |
| 77–82 | N | Atividades administrativas e serviços complementares |
| 84 | O | Administração pública, defesa e seguridade social |
| 85 | P | Educação |
| 86–88 | Q | Saúde humana e serviços sociais |
| 90–93 | R | Artes, cultura, esporte e recreação |
| 94–96 | S | Outras atividades de serviços |
| 97 | T | Serviços domésticos |
| 99 | U | Organismos internacionais |

(Tabela Censo a ser preenchida na próxima iteração da Etapa 1.)

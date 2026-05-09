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

(Documentar aqui após execução: trimestre baixado, hash dos arquivos, decisões de harmonização.)

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

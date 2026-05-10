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

## ADR-005 — Parser PNADC: layout fixo do input SAS oficial, sem dependência de terceiros

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** Para ler microdados PNADC em layout fixo precisamos das posições e larguras de cada coluna no arquivo `.txt` interno do ZIP do IBGE. Existem três caminhos:

1. **Pacote de terceiros** (`PNADcIBGE` em R, `python-microdadosbrasil`, `basedosdados`) — consome as bases já tratadas. Vantagem: rápido. Desvantagem: trazem dependências pesadas, podem aplicar filtros/recodificações silenciosas, atualizam fora do nosso ciclo, e o `basedosdados` historicamente serve dados via BigQuery/parquet **agregados ou pré-processados**, o que conflita com ADR-004 (microdados brutos obrigatórios).
2. **Hard-code do layout** dentro do código — frágil e não rastreável; o layout muda quando o IBGE publica novo dicionário.
3. **Parser do input SAS oficial** (`input_PNADC_trimestral.sas`) que o próprio IBGE distribui em `Documentacao/Dicionario_e_input_20221031.zip` — a fonte canônica. Cada linha do SAS tem `@<posicao> <NOME> [$]<largura>.`, fácil de extrair com regex.

**Decisão:** Adotar a opção (3). A função `_carregar_layout()` em `src/ingest/pnadc.py` baixa o ZIP de documentação do IBGE (idempotente), extrai o `input_PNADC_trimestral.sas` e parseia via regex `@(\d+)\s+(\w+)\s+(\$)?(\d+)\.`. O resultado é um DataFrame `(nome, inicio, tamanho, tipo)` que alimenta `pd.read_fwf` com `colspecs` 0-based. Seleciona-se um subset de ~37 variáveis (`VARIAVEIS_ALVO`) em vez das ~420 disponíveis, para conter memória. O dicionário também é versionado como artefato em `data/raw/pnadc/`.

**Consequências:**

- (+) Sem dependência externa além de `pandas` + `requests` (já no projeto).
- (+) Parser sobrevive a futuras revisões do layout PNADC desde que o input SAS oficial siga a mesma sintaxe (estável desde 2014).
- (+) Conformidade total com ADR-004: lemos o microdado bruto, sem intermediários.
- (+) Encoding Latin-1 declarado explicitamente — evita corrupção silenciosa.
- (−) Se o IBGE publicar dicionário com sufixo de data diferente, é preciso atualizar `DICIONARIO_ZIP_URL`. Mitigação: monitorar `Documentacao/`.
- (−) Lemos cada arquivo trimestral inteiro em memória (~500 mil linhas × 37 colunas ≈ 12 MB parquet) — confortável; se passarmos para microdados anuais (~3 M linhas), avaliar leitura em chunks.

## ADR-006 — Ingestão MEI: snapshot 2026-04, sem `Empresas*.zip`, definição de "ativo"

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** Os Dados Abertos CNPJ da Receita Federal são publicados mensalmente. Um snapshot completo soma ~25 GB (Empresas + Estabelecimentos + Sócios + Simples + auxiliares). Para o projeto interessam apenas as pessoas com opção MEI ativa, não todo o universo CNPJ. Além disso, a partir de janeiro/2026 a RFB migrou os arquivos para um Nextcloud público em `arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9` — URLs antigas (`https://arquivos.receitafederal.gov.br/dados/cnpj/...` e `https://dadosabertos.rfb.gov.br/CNPJ/`) retornam 404 ou são inacessíveis. Há ambiguidade sobre o que é "MEI ativo": pode-se filtrar por (a) opção MEI no Simples; (b) situação cadastral do estabelecimento; (c) interseção dos dois.

**Decisão:**

1. **Snapshot:** usar `2026-04` (último estável disponível em 09/05/2026). Snapshots futuros podem ser ingeridos sob demanda — basta `python -m src.ingest.mei --periodo YYYY-MM`.
2. **Endpoint:** WebDAV público do Nextcloud RFB. URL canônica `https://arquivos.receitafederal.gov.br/public.php/webdav/<YYYY-MM>/<arquivo>.zip` com Basic Auth (user = share token `YggdBLfdninEJX9`, password vazia). Documentado na docstring de `src/ingest/mei.py` e em memória persistente do agente.
3. **NÃO baixar `Empresas*.zip`:** essa tabela traz razão social, capital social e porte — nenhum desses campos é necessário para os recortes da Etapa 2 (UF × CNAE × estrato demográfico). Economiza ~5 GB de download e o tempo correspondente. Se for necessário enriquecer com razão social no futuro (ex.: análise qualitativa por nome), basta voltar e baixar.
4. **NÃO baixar `Socios*.zip`:** sócios são irrelevantes para MEI (que é sempre titular único).
5. **Definição operacional de "MEI ativo":** combinação dos dois critérios em ordem:
    a) **Vigência da opção MEI** no Simples: `opcao_mei = 'S'` E `data_exclusao_mei` vazia/`'0'` → captura quem é MEI no momento, excluindo ex-MEI já desenquadrados.
    b) **Situação cadastral do estabelecimento matriz:** `situacao_cadastral = '02'` (ativa) na tabela Estabelecimentos. Estabelecimentos suspensos (`'03'`), inaptos (`'04'`) ou baixados (`'08'`) **não** são contados como MEI ativo, mesmo que ainda figurem no Simples.
6. **Coluna persistida:** `mei_ativo: bool = (situacao_cadastral == '02')`, calculada sobre o universo já restrito a MEI vigente. Permite ao consumidor da Etapa 2 escolher entre "MEI vigente" (todos) ou "MEI ativo" (situação 02) sem refazer o filtro.
7. **Identificador de matriz:** `identificador_matriz_filial = '1'` (matriz). MEI por construção tem 1 estabelecimento — o filtro elimina duplicação quando algum CNPJ MEI eventualmente tem filial registrada.

**Consequências:**

- (+) Download reduzido em ~5 GB (~25%) sem perder informação relevante para o estudo.
- (+) Definição de "ativo" alinhada à prática de mercado (Sebrae publica seus rankings por situação cadastral '02').
- (+) Resultado validado: 13.274.159 MEI ativos no Brasil em 2026-04 — bate com a ordem de grandeza esperada (estatísticas Sebrae em torno de 13-15 milhões na janela 2025-2026).
- (+) Top UFs (SP, MG, RJ, PR, RS) e top seções CNAE (G, H, S, C, I) compatíveis com publicações oficiais.
- (−) Se o estudo da ABEVD vier a exigir análise por razão social ou capital social, será preciso ingestão adicional de `Empresas*.zip` (~5 GB) — o pipeline já está estruturado para isso.
- (−) `municipio_codigo_ibge` ficou vazio (apenas o código RFB foi resolvido). Se análises municipais forem necessárias na Etapa 3, implementar de-para RFB→IBGE via `Municipios.zip` cruzado com a tabela IBGE de municípios. Pendência registrada.

## ADR-007 — Censo 2022: pular Etapa 1 e seguir só com PNADC + MEI

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** A minuta técnica prevê três fontes na Etapa 1: PNAD Contínua, Censo Demográfico e Cadastro MEI. PNADC e MEI já foram ingeridos (ADR-005 e ADR-006). Antes de baixar o Censo, verificamos a disponibilidade dos **microdados da Amostra do Censo Demográfico 2022** — única fração do Censo que carrega as variáveis de trabalho/ocupação/renda necessárias para nossos recortes. Resultado da verificação em 2026-05-09:

- O FTP oficial `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/` contém apenas Resultados do Universo e agregações por setor censitário. **Não há pasta de Microdados da Amostra.**
- A divulgação oficial estava agendada para 04/12/2025 e foi **adiada sem nova data** ([nota IBGE](https://www.ibge.gov.br/novo-portal-erramos/45278-adiamento-das-divulgacoes-censo-demografico-2022-microdados-da-amostra-e-censo-demografico-2022-areas-de-ponderacao.html)). Justificativa oficial: adequação à LGPD e a boas práticas internacionais de estatísticas oficiais.
- As alternativas seriam: (a) Censo 2010 (15 anos defasado, contrário à intenção da minuta de retratar cenário atual); (b) consumir agregados por setor censitário do Censo 2022 (viola ADR-004 — só microdados); (c) esperar publicação (prazo indefinido bloqueia entregáveis).

**Decisão:** Concluir a Etapa 1 **sem o Censo 2022**, com PNADC + MEI. Razões:

1. A minuta usa Censo como "**referência estrutural em nível municipal**" — complementar à PNADC, não substitutivo. PNADC sozinha é representativa por UF, que é a granularidade exigida pelos objetivos do estudo.
2. As variáveis demográficas e econômicas centrais do estudo (sexo, idade, cor/raça, escolaridade, posição na ocupação, rendimento, CNAE) estão na PNADC.
3. MEI cobre a dimensão de formalização — completa o triângulo informal (PNADC) × formal (MEI) sem depender do Censo.
4. Aguardar prazo indefinido bloqueia o cronograma da minuta (3 meses).

Quando o IBGE publicar os Microdados da Amostra, **rodar `python -m src.ingest.censo --tabela amostra` para enriquecer com:**

- Análise em nível municipal (densidade, perfil demográfico subestadual)
- Validação cruzada das estimativas estaduais da PNADC
- Recortes por situação domiciliar (urbano/rural) com maior precisão

**Consequências:**

- (+) Cronograma do projeto preservado.
- (+) Entregáveis (Etapas 2-4) podem prosseguir sem dependência externa em prazo aberto.
- (+) Decisão totalmente rastreável no relatório final via este ADR.
- (−) Análise municipal fica fora do escopo desta versão. Será retomada em iteração futura sob demanda da ABEVD ou quando publicada a Amostra.
- (−) Validação cruzada PNADC × Censo (recomendada pela boa prática) não pode ser feita agora — somente comparação com publicações tabulares do IBGE/PNADC anterior.

**Pendência registrada em `src/ingest/censo.py`:** o esqueleto da função fica como `NotImplementedError` com comentário apontando para este ADR.

## ADR-008 — Tratamento de estratos com 1 só UPA: `single_psu=certainty`

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** No desenho amostral PNADC, alguns estratos contêm apenas 1 UPA (caso de regiões metropolitanas/RIDEs com 1 setor único). O estimador de variância de Taylor exige ≥ 2 PSUs por estrato — sem isso, lança `ValueError: Only one PSU in the following strata`. A biblioteca `samplics` oferece 4 tratamentos: `error` (default), `skip` (descarta), `certainty` (variância 0 nesses estratos), `combine` (junta com adjacente).

**Decisão:** Usar `single_psu=SinglePSUEst.certainty`. Razões:

1. É a opção que mantém todos os registros na estimativa (sem viés de descarte como `skip`).
2. Não exige escolha arbitrária de "estrato adjacente" como `combine`.
3. Subestima ligeiramente a variância apenas nos estratos singleton (um número pequeno: ~5 estratos de >1.500 — impacto agregado < 1%).
4. É a prática padrão do IBGE para publicações com Taylor.

**Consequências:**

- (+) Estimativas robustas mesmo com estratos singleton.
- (+) IC 95% reportáveis para todas as UFs.
- (−) Variância marginalmente subestimada nos estratos com 1 UPA. Em CV agregados (4-5%), o efeito é desprezível mas vale registrar nas limitações do relatório técnico.

---

## ADR-009 — Derivação de `cnae_secao` a partir de `V4013` (PNADC)

**Data:** 2026-05-09
**Status:** aceito

**Contexto:** Ao processar a série PNADC 2025 (T1-T4), descobrimos que a variável `V40132` — historicamente a "seção CNAE Domiciliar 2.0 já em letra A-U" — vem **vazia** nas divulgações 2025. O dicionário oficial ainda lista `V40132` como variável existente, mas o IBGE deixou de preenchê-la. Já a variável `V4013` (CNAE Domiciliar 2.0, 5 dígitos) continua preenchida.

**Decisão:** Derivar `cnae_secao` (letra A-U) a partir dos 2 primeiros dígitos de `V4013` (a "divisão" CNAE), via tabela divisão→seção definida em `src/ingest/mei.py::CNAE_DIVISAO_TO_SECAO` (mesma usada para o Cadastro MEI). A tabela `V4013` cobre todas as divisões 1-99 conforme estrutura CNAE 2.0/2.3 — o mapeamento é estável.

**Consequências:**

- (+) Compatibilidade total entre PNADC e MEI no nível de seção (vocabulário comum).
- (+) Sem perda de informação relevante: para análises da Etapa 2/3, seção é a granularidade necessária.
- (−) Cerca de 14% dos nano-empreendedores aparecem com `cnae_secao = NaN` (V4013 ausente — provavelmente registros de pessoas que se declararam ocupadas mas não detalharam a atividade). Tratar como categoria "não declarada" nos perfis e flagged como pendência se a fração subir em séries futuras.

---

(Próximas decisões a registrar pelos agentes ao longo da execução.)

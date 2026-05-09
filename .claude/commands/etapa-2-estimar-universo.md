---
description: Etapa 2 — Estimativa do Universo de Nano-empreendedores (recorte renda + expansão amostral + cruzamento MEI)
argument-hint: [UF opcional para análise focada, ex: SP]
---

Você vai conduzir a **Etapa 2** do projeto Nano-empreendedores ABEVD/FGV NPII: estimativa do universo.

**Argumento (se fornecido):** $ARGUMENTS — UF para análise focada. Se vazio, gerar para todas as UFs.

## Pré-condições

- A Etapa 1 deve ter sido executada (`data/processed/` populado).
- Se faltar base, peça `/etapa-1-preparar-bases` antes de prosseguir.

## Roteiro

1. **Verificar pré-condições**: confira `data/processed/` e os metadados.
2. **Confirmar com o usuário** as definições operacionais antes da primeira execução:
   - Renda anual ≤ R$ 40 mil = bruta? inclui só trabalho ou todas as fontes? (default: bruta, só trabalho — conforme leitura da minuta)
3. **Delegar ao subagente `statistician`**:
   > Execute a Etapa 2. Aplique o recorte de nano-empreendedor sobre a base PNADC processada, expanda com pesos amostrais respeitando o desenho complexo, e cruze por estrato (UF × CNAE × sexo × faixa etária) com o MEI. Gere tabelas em outputs/tabelas/etapa2/ (CSV + parquet) com IC 95%. Atualize docs/metodologia.md (seção Etapa 2). Reporte totais Brasil, top-5 UFs, e percentual de formalização.
4. **Validar**: existem `nano_total_uf.csv`, `nano_formalizacao_uf.csv`, `nano_por_regiao.csv`?
5. **Sanity check**: o total Brasil estimado é compatível com a ordem de grandeza esperada (a minuta cita ~25 milhões de conta-própria total; o subconjunto ≤ R$ 40 mil deve ser menor mas substancial)?
6. **Reporte ao usuário** os números-chave e sugira a Etapa 3.

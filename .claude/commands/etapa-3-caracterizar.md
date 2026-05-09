---
description: Etapa 3 — Caracterização Socioeconômica dos Nano-empreendedores (perfis demográficos, econômicos, territoriais)
argument-hint: [recorte opcional, ex: "mulheres-comercio" ou "regiao-norte"]
---

Você vai conduzir a **Etapa 3** do projeto Nano-empreendedores ABEVD/FGV NPII: caracterização socioeconômica.

**Argumento (se fornecido):** $ARGUMENTS — recorte analítico de interesse (default: análise completa).

## Pré-condições

- Etapas 1 e 2 concluídas (`outputs/tabelas/etapa2/` populado).

## Roteiro

1. **Verificar pré-condições**: liste `outputs/tabelas/etapa2/` e confirme que as estimativas existem.
2. **Delegar ao subagente `socioeconomic-analyst`**:
   > Execute a Etapa 3. A partir das bases processadas e estimativas da Etapa 2, construa perfis (a) demográfico, (b) econômico, (c) territorial dos nano-empreendedores por UF, sempre com pesos amostrais. Gere tabelas em outputs/tabelas/etapa3/, gráficos exploratórios em outputs/graficos/etapa3/ (PNG + HTML interativo), e memorial em docs/analises-etapa3.md. Destaque o recorte estratégico para a ABEVD: mulheres adultas em comércio e serviços pessoais, por UF. Recorte adicional: {arg ou "nenhum"}.
3. **Validar entregáveis**: tabelas demográfica, econômica, setorial e comparativo regional + gráficos.
4. **Reporte achados-chave**: top UFs por densidade, perfil da maioria, heterogeneidade regional, oportunidades para a ABEVD.
5. Sugira a Etapa 4 (relatório final).

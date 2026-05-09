---
description: Etapa 1 — Preparação e Formatação das Bases de Dados (PNADC, Censo, MEI)
argument-hint: [trimestre PNADC opcional, ex: 2024Q4]
---

Você vai conduzir a **Etapa 1** do projeto Nano-empreendedores ABEVD/FGV NPII: preparação e formatação das bases.

**Argumento (se fornecido):** $ARGUMENTS — trimestre da PNADC a usar (ex.: `2024Q4`). Se vazio, usar o último trimestre disponível.

## Roteiro

1. **Verificar o estado atual**: rode `ls data/raw/` e `ls data/processed/` para ver o que já existe.
2. **Delegar a execução** ao subagente `data-engineer` via Agent tool, com prompt:
   > Execute a Etapa 1 do projeto. Trimestre PNADC alvo: {trimestre ou "último disponível"}. Baixe (se necessário), padronize e gere parquet em data/processed/ para PNADC, Censo e MEI. Atualize docs/dicionario-dados.md e docs/decisoes-tecnicas.md. Reporte resumo final com arquivos gerados, contagens e próximos passos.
3. **Validar o entregável**: confira que existem `data/processed/pnadc_*.parquet`, `data/processed/censo_*.parquet`, `data/processed/mei_*.parquet` e que `docs/dicionario-dados.md` foi atualizado.
4. **Avisar o usuário** com o resumo retornado pelo agente e sugira a Etapa 2.

Não execute downloads diretamente — sempre via subagente para isolar logs pesados do contexto principal.

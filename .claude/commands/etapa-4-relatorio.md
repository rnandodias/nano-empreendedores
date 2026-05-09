---
description: Etapa 4 — Elaboração do Relatório Técnico Final, Sumário Executivo e Apresentação (PPTX)
argument-hint: [versão opcional, ex: v1, final]
---

Você vai conduzir a **Etapa 4** do projeto Nano-empreendedores ABEVD/FGV NPII: relatório final.

**Argumento (se fornecido):** $ARGUMENTS — sufixo de versão para os arquivos gerados.

## Pré-condições

- Etapas 1, 2 e 3 concluídas (todos os entregáveis em `outputs/`).
- `docs/metodologia.md`, `docs/analises-etapa3.md` e `docs/dicionario-dados.md` atualizados.

## Roteiro

1. **Verificar pré-condições**: liste `outputs/tabelas/`, `outputs/graficos/`, `docs/`.
2. **Confirmar com o usuário** o escopo final:
   - Já podemos gerar versão final ou é uma versão preliminar (draft)?
   - Algum recorte ou recomendação específica que ele quer destacar?
3. **Delegar ao subagente `report-writer`**:
   > Execute a Etapa 4. Consolide os entregáveis das Etapas 2 e 3 em três produtos: (1) Relatório Técnico Final em PDF, (2) Sumário Executivo PDF (4-6 pgs), (3) Apresentação Executiva PPTX (15-20 slides). Use templates em src/report/templates/. Versão: {arg ou "v1"}. Toda afirmação numérica deve ter referência à tabela de origem. Inclua seção de limitações e recomendações concretas para a ABEVD por UF. Reporte caminhos dos arquivos gerados e contagem de páginas/slides.
4. **Validar**: os 3 arquivos existem em `outputs/relatorios/`? Conferir tamanhos razoáveis.
5. **Reporte ao usuário** os arquivos finais e sugira revisão antes de envio externo.

## Importante

Não envie nem publique os entregáveis para nenhum stakeholder externo sem aprovação explícita do usuário.

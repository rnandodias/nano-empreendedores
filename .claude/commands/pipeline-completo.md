---
description: Executa o pipeline completo das Etapas 1 → 2 → 3 → 4 sequencialmente, com checkpoints
argument-hint: [trimestre PNADC opcional, ex: 2024Q4]
---

Você vai conduzir o **pipeline completo** do projeto Nano-empreendedores ABEVD/FGV NPII, executando as 4 etapas em sequência.

**Argumento:** $ARGUMENTS — trimestre PNADC alvo (default: último disponível).

## Roteiro

Execute as etapas via os respectivos slash commands, em sequência, **parando em cada checkpoint** para confirmar com o usuário antes de prosseguir:

1. `/etapa-1-preparar-bases $ARGUMENTS`
   - **Checkpoint**: confirme com o usuário que as bases foram baixadas e estão íntegras antes de seguir.
2. `/etapa-2-estimar-universo`
   - **Checkpoint**: revise o sanity check (totais Brasil) com o usuário.
3. `/etapa-3-caracterizar`
   - **Checkpoint**: confirme que os perfis fazem sentido e não há regressão de dados.
4. `/etapa-4-relatorio`
   - **Checkpoint final**: aguarde aprovação do usuário antes de gerar versão "final".

## Princípios

- **Pare em qualquer falha** e diagnostique antes de continuar — não tente "consertar" pulando etapas.
- Pipeline completo do zero (incluindo download do Censo) pode levar **horas**. Avise o usuário no início e ofereça rodar etapas isoladas se ele já tem dados baixados.

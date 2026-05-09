"""Harmonização de classificações entre fontes.

CNAE (versões 2.0 vs 2.3), categorias de cor/raça, escolaridade e ocupação.
Mantém um único vocabulário interno do projeto, documentado em docs/dicionario-dados.md.
"""

from __future__ import annotations

import pandas as pd


def harmonize_cnae(df: pd.DataFrame, col: str, versao_origem: str = "2.0") -> pd.DataFrame:
    """Converte CNAE da versão de origem para o vocabulário interno do projeto."""
    raise NotImplementedError("TODO: tabela de-para CNAE 2.0 ↔ 2.3 ↔ seções A-U")


def harmonize_cor_raca(df: pd.DataFrame, col: str, fonte: str) -> pd.DataFrame:
    """Padroniza categorias de cor/raça entre PNADC, Censo e MEI."""
    raise NotImplementedError("TODO: mapeamento de categorias")


def harmonize_escolaridade(df: pd.DataFrame, col: str, fonte: str) -> pd.DataFrame:
    """Padroniza escolaridade em: sem instrução, fundamental, médio, superior."""
    raise NotImplementedError("TODO: mapeamento")


def harmonize_posicao_ocupacao(df: pd.DataFrame, col: str, fonte: str) -> pd.DataFrame:
    """Padroniza posição na ocupação, marcando claramente 'conta-própria'."""
    raise NotImplementedError("TODO: mapeamento")

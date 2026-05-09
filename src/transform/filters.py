"""Recortes da definição operacional de nano-empreendedor."""

from __future__ import annotations

import pandas as pd

# Definição operacional — pode ser ajustada após validação com o usuário/cliente.
TETO_RENDA_ANUAL_BRL: float = 40_000.0
MESES_REFERENCIA: int = 12


def is_conta_propria(df: pd.DataFrame, col_posicao: str) -> pd.Series:
    """Booleano: pessoa classificada como trabalhador por conta própria (vocab harmonizado)."""
    return df[col_posicao].eq("conta_propria")


def renda_anual(df: pd.DataFrame, col_renda_mensal: str) -> pd.Series:
    """Anualiza rendimento mensal habitual (mensal × 12)."""
    return df[col_renda_mensal].fillna(0).astype(float) * MESES_REFERENCIA


def is_nano_empreendedor(
    df: pd.DataFrame,
    col_posicao: str,
    col_renda_mensal: str,
    teto: float = TETO_RENDA_ANUAL_BRL,
) -> pd.Series:
    """Booleano: pessoa atende à definição de nano-empreendedor."""
    return is_conta_propria(df, col_posicao) & (renda_anual(df, col_renda_mensal) <= teto)

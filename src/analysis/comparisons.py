"""Comparações interestaduais e regionais."""

from __future__ import annotations

import pandas as pd

REGIOES = {
    "N":  ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "NE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "CO": ["DF", "GO", "MS", "MT"],
    "SE": ["ES", "MG", "RJ", "SP"],
    "S":  ["PR", "RS", "SC"],
}

UF_TO_REGIAO = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}


def agregar_por_regiao(df: pd.DataFrame, col_uf: str = "uf") -> pd.DataFrame:
    """Agrega métricas estaduais por região (N, NE, CO, SE, S)."""
    raise NotImplementedError("TODO")


def densidade_relativa(
    estimativas_nano: pd.DataFrame,
    populacao_ocupada_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula nano_estimado / pop_ocupada_uf — densidade relativa por UF."""
    raise NotImplementedError("TODO")


def ranking_uf(df: pd.DataFrame, metrica: str, top: int = 5, ascendente: bool = False) -> pd.DataFrame:
    """Ranking das UFs em uma métrica (top ou bottom)."""
    raise NotImplementedError("TODO")

"""Tabelas formatadas para o relatório (great-tables)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def tabela_estimativas_uf(df: pd.DataFrame, out_html: Path) -> None:
    """Tabela formatada das estimativas por UF, com IC 95% e formalização."""
    raise NotImplementedError("TODO: usar great_tables.GT()")


def tabela_perfil_demografico(df: pd.DataFrame, out_html: Path) -> None:
    """Tabela formatada do perfil demográfico por UF."""
    raise NotImplementedError("TODO")

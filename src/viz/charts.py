"""Gráficos do relatório.

Convenções:
- PNG (alta DPI) para o PDF impresso.
- HTML interativo (Plotly) para análise exploratória.
- Paleta com identidade visual sóbria (institucional).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PALETA_INSTITUCIONAL = {
    "primaria": "#1B3A57",
    "secundaria": "#D9A441",
    "neutro": "#6B7280",
    "destaque": "#B0413E",
}


def barras_uf(
    df: pd.DataFrame,
    col_x: str,
    col_y: str,
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,
) -> None:
    """Barras horizontais por UF, ordenadas pela métrica."""
    raise NotImplementedError("TODO: matplotlib + opcional plotly")


def mapa_coropletico_uf(
    df: pd.DataFrame,
    col_uf: str,
    col_metrica: str,
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,
) -> None:
    """Mapa coroplético do Brasil por UF (geopandas + shapefile IBGE)."""
    raise NotImplementedError("TODO: usar shapefile UF do IBGE")


def piramide_etaria(
    df: pd.DataFrame,
    col_idade: str,
    col_sexo: str,
    col_peso: str,
    titulo: str,
    out_png: Path,
) -> None:
    """Pirâmide etária ponderada da população nano-empreendedora."""
    raise NotImplementedError("TODO")

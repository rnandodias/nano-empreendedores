"""Perfis socioeconômicos dos nano-empreendedores (Etapa 3).

Sempre com pesos amostrais. Reportar n amostral além do estimado expandido.
"""

from __future__ import annotations

import pandas as pd


def perfil_demografico(df: pd.DataFrame, col_peso: str, col_uf: str) -> pd.DataFrame:
    """Distribuição por sexo, faixa etária, cor/raça, escolaridade — por UF."""
    raise NotImplementedError("TODO")


def perfil_economico(df: pd.DataFrame, col_peso: str, col_uf: str) -> pd.DataFrame:
    """Renda média/mediana, jornada, tempo na ocupação — por UF."""
    raise NotImplementedError("TODO")


def perfil_setorial(df: pd.DataFrame, col_peso: str, col_uf: str, col_cnae: str) -> pd.DataFrame:
    """Distribuição por setor CNAE (seções A-U) — por UF."""
    raise NotImplementedError("TODO")


def recorte_mulheres_comercio_servicos(df: pd.DataFrame, col_peso: str, col_uf: str) -> pd.DataFrame:
    """Recorte estratégico para a ABEVD: mulheres adultas (25-49) em Comércio (G) e
    Serviços pessoais (S), por UF — base potencial para expansão de consultoras."""
    raise NotImplementedError("TODO")

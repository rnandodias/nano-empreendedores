"""Estimativa do universo de nano-empreendedores (Etapa 2).

Aplica o recorte da definição operacional, expande pela amostra (pesos PNADC/Censo),
e cruza por estrato com o cadastro MEI para distinguir formal vs. informal.

PNADC tem desenho amostral complexo (UPA, estrato, pesos calibrados V1028).
Use `samplics` ou implementação manual com cuidado para variância correta.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class EstimativaUF:
    uf: str
    n_amostral: int
    total_estimado: float
    ic95_low: float
    ic95_high: float
    formalizados_mei: float
    informais: float


def estimar_universo_uf(
    df_pnadc: pd.DataFrame,
    col_peso: str = "V1028",
    col_uf: str = "UF",
) -> pd.DataFrame:
    """Estima total de nano-empreendedores por UF, com IC 95%.

    Returns:
        DataFrame com colunas: uf, n_amostral, total_estimado, ic95_low, ic95_high.
    """
    raise NotImplementedError("TODO: implementar com samplics respeitando UPA/Estrato")


def cruzar_com_mei(
    estimativas_uf: pd.DataFrame,
    df_mei: pd.DataFrame,
    teto_renda_mei: float = 81_000.0,
) -> pd.DataFrame:
    """Cruza estimativas com cadastro MEI por UF (e CNAE quando disponível).

    Atenção: o teto MEI (~R$ 81 mil/ano até 2024) é maior que o teto nano (R$ 40 mil).
    Apenas uma fração dos MEI é nano-empreendedor — isso precisa ser tratado.
    """
    raise NotImplementedError("TODO: cruzamento agregado por estrato")


def salvar_resultados(estimativas: pd.DataFrame, out_dir: Path) -> None:
    """Salva tabelas em CSV + parquet em outputs/tabelas/etapa2/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    estimativas.to_csv(out_dir / "nano_total_uf.csv", index=False, encoding="utf-8-sig")
    estimativas.to_parquet(out_dir / "nano_total_uf.parquet", index=False)

"""Comparações interestaduais e regionais.

Funções utilitárias que operam sobre as saídas de ``universe_estimator.py``
e ``profiles.py``. Não fazem nova ingestão — apenas agregam/comparam.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Mapeamento UF -> Região (codificação IBGE)
# ---------------------------------------------------------------------------

REGIOES: dict[str, list[str]] = {
    "Norte":        ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste":     ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste":      ["ES", "MG", "RJ", "SP"],
    "Sul":          ["PR", "RS", "SC"],
}

UF_TO_REGIAO: dict[str, str] = {
    uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs
}


def adicionar_regiao(df: pd.DataFrame, col_uf: str = "uf") -> pd.DataFrame:
    """Adiciona coluna ``regiao`` baseada na sigla da UF."""
    out = df.copy()
    out["regiao"] = out[col_uf].map(UF_TO_REGIAO)
    return out


# ---------------------------------------------------------------------------
# Agregação por região
# ---------------------------------------------------------------------------

def agregar_por_regiao(
    df: pd.DataFrame,
    col_uf: str = "uf",
    cols_soma: tuple[str, ...] = (
        "n_amostral",
        "n_amostral_cp",
        "n_amostral_nano",
        "total_cp_estimado",
        "total_nano_estimado",
        "mei_ativos_total",
        "informais_aprox",
    ),
    col_periodo: str | None = "periodo",
) -> pd.DataFrame:
    """Soma as colunas estaduais por região (e por período, se existir).

    Recalcula taxa_formalizacao no nível regional para coerência aritmética
    (não é a média das taxas estaduais — é a razão das somas).
    """
    df = adicionar_regiao(df, col_uf=col_uf)
    cols = [c for c in cols_soma if c in df.columns]
    grupo = ["regiao"] if col_periodo not in df.columns else [col_periodo, "regiao"]
    res = df.groupby(grupo, observed=True)[cols].sum().reset_index()

    if {"mei_ativos_total", "total_nano_estimado"}.issubset(res.columns):
        res["taxa_formalizacao_aprox"] = (
            res["mei_ativos_total"] / res["total_nano_estimado"]
        ).clip(upper=1.0).round(4)
    if {"total_nano_estimado", "total_cp_estimado"}.issubset(res.columns):
        res["share_nano_em_cp"] = (
            res["total_nano_estimado"] / res["total_cp_estimado"]
        ).round(4)
    return res


# ---------------------------------------------------------------------------
# Densidade relativa (nano por 100 habitantes ocupados)
# ---------------------------------------------------------------------------

def densidade_relativa(
    estimativas_nano: pd.DataFrame,
    populacao_ocupada_uf: pd.DataFrame,
    col_uf: str = "uf",
    col_pop: str = "populacao_ocupada",
) -> pd.DataFrame:
    """Calcula ``densidade_nano_pct = nano_estimado / pop_ocupada × 100``.

    Args:
        estimativas_nano: saída do universe_estimator (deve ter
            ``total_nano_estimado``).
        populacao_ocupada_uf: DataFrame com (uf, populacao_ocupada).
            Pode vir da própria PNADC (estimativa de pop. ocupada por UF) ou
            de uma tabela auxiliar.

    Returns:
        DataFrame com colunas adicionais ``populacao_ocupada`` e
        ``densidade_nano_pct``.
    """
    out = estimativas_nano.merge(
        populacao_ocupada_uf[[col_uf, col_pop]], on=col_uf, how="left"
    )
    out["densidade_nano_pct"] = (
        100 * out["total_nano_estimado"] / out[col_pop]
    ).round(2)
    return out


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

def ranking_uf(
    df: pd.DataFrame,
    metrica: str,
    top: int = 5,
    ascendente: bool = False,
    col_uf: str = "uf",
) -> pd.DataFrame:
    """Top (ou bottom) ``top`` UFs ordenadas por ``metrica``.

    Args:
        df: DataFrame com 1 linha por UF.
        metrica: nome da coluna pra ordenar.
        top: quantas UFs retornar.
        ascendente: True = bottom-N (menores valores).
    """
    if metrica not in df.columns:
        raise ValueError(f"Métrica '{metrica}' não encontrada em {list(df.columns)}")
    return (
        df.sort_values(metrica, ascending=ascendente)
        .head(top)
        [[col_uf, metrica]]
        .reset_index(drop=True)
    )


def variacao_periodo(
    df_serie: pd.DataFrame,
    metrica: str,
    col_periodo: str = "periodo",
    col_uf: str = "uf",
) -> pd.DataFrame:
    """Tabela larga: período × UF para uma métrica, com coluna de variação
    (último período − primeiro período) absoluta e percentual.

    Útil para identificar UFs onde a tendência de crescimento (ou queda) é
    mais acentuada — insight chave para estratégia da ABEVD.
    """
    pivot = df_serie.pivot_table(
        index=col_uf, columns=col_periodo, values=metrica, aggfunc="first"
    )
    periodos_ord = sorted(pivot.columns)
    if len(periodos_ord) < 2:
        return pivot.reset_index()
    primeiro, ultimo = periodos_ord[0], periodos_ord[-1]
    pivot["delta_abs"] = pivot[ultimo] - pivot[primeiro]
    pivot["delta_pct"] = (100 * pivot["delta_abs"] / pivot[primeiro]).round(1)
    return pivot.reset_index()

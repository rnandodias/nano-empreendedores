"""Perfis socioeconômicos dos nano-empreendedores (Etapa 3).

Cada função:
- Filtra para nano-empreendedores (definição operacional em ``filters.py``).
- Agrupa por UF (e, opcionalmente, outras dimensões).
- Pondera com ``peso_amostral`` (V1028) — estimativas sem peso são inválidas
  para PNADC.
- Retorna DataFrame com colunas estimadas + ``n_amostral`` para diagnóstico.

Convenções:
- Idade em faixas: 14-24 (jovem), 25-49 (adulto), 50+ (maduro).
- Renda em R$ correntes do trimestre (sem deflação por enquanto — ver ADR
  futuro se for necessário deflacionar para a série temporal).
- Saídas em ``outputs/tabelas/etapa3/``.

Compatível com a série temporal: cada função aceita um ``df`` único; a
orquestração da série fica em ``serie_temporal_perfis()``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src import paths
from src.analysis.universe_estimator import (
    COL_PESO, COL_UF, carregar_pnadc_processado, marcar_nano,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

COL_SEXO = "sexo"
COL_IDADE = "idade_anos"
COL_COR = "cor_raca"
COL_ESCOLARIDADE = "escolaridade"
COL_RENDA = "renda_mensal_brl"
COL_CNAE_SECAO = "cnae_secao"

FAIXAS_ETARIAS = [
    (14, 24, "jovem_14_24"),
    (25, 49, "adulto_25_49"),
    (50, 200, "maduro_50_mais"),
]


def _faixa_etaria(idade: int | float) -> str | None:
    if pd.isna(idade):
        return None
    idade = int(idade)
    for ini, fim, label in FAIXAS_ETARIAS:
        if ini <= idade <= fim:
            return label
    return None


# ---------------------------------------------------------------------------
# Helpers de agregação ponderada
# ---------------------------------------------------------------------------

def _share_ponderado(
    df: pd.DataFrame,
    grupo: list[str],
    col_peso: str = COL_PESO,
) -> pd.DataFrame:
    """Distribuição ponderada (% e total expandido) por combinação de ``grupo``.

    Returns:
        DataFrame com colunas: *grupo, n_amostral, total_expandido, share_pct.
    """
    g = df.groupby(grupo, observed=True, dropna=False)
    res = pd.DataFrame({
        "n_amostral": g.size(),
        "total_expandido": g[col_peso].sum(),
    }).reset_index()
    # Share dentro de cada combinação dos grupos exceto o último
    if len(grupo) > 1:
        denom = res.groupby(grupo[:-1], observed=True)["total_expandido"].transform("sum")
        res["share_pct"] = (100 * res["total_expandido"] / denom).round(2)
    else:
        total = res["total_expandido"].sum()
        res["share_pct"] = (100 * res["total_expandido"] / total).round(2)
    return res


def _media_ponderada(
    df: pd.DataFrame,
    col_valor: str,
    grupo: list[str],
    col_peso: str = COL_PESO,
) -> pd.DataFrame:
    """Média ponderada de ``col_valor`` por ``grupo``."""
    val = df[col_valor].astype(float)
    peso = df[col_peso].astype(float)
    df2 = df.assign(_v=val * peso, _w=peso)
    g = df2.groupby(grupo, observed=True)
    res = pd.DataFrame({
        "n_amostral": g.size(),
        "media": g["_v"].sum() / g["_w"].sum(),
        "soma_pesos": g["_w"].sum(),
    }).reset_index()
    return res


def _mediana_ponderada(valores: np.ndarray, pesos: np.ndarray) -> float:
    """Mediana ponderada (interpolação linear no CDF)."""
    if len(valores) == 0:
        return float("nan")
    ordem = np.argsort(valores)
    v = valores[ordem]
    w = pesos[ordem]
    cum = np.cumsum(w)
    corte = cum[-1] / 2.0
    idx = np.searchsorted(cum, corte)
    return float(v[min(idx, len(v) - 1)])


# ---------------------------------------------------------------------------
# Perfis individuais
# ---------------------------------------------------------------------------

def perfil_demografico(df_pnadc: pd.DataFrame) -> pd.DataFrame:
    """Distribuição por sexo, faixa etária, cor/raça e escolaridade — por UF.

    Filtra para nano-empreendedores. Cada linha é uma combinação
    (uf, dimensao, valor) com share % dentro da UF.
    """
    df = marcar_nano(df_pnadc)
    df = df[df["is_nano"]].copy()
    df["faixa_etaria"] = df[COL_IDADE].map(_faixa_etaria)

    blocos: list[pd.DataFrame] = []
    for dim_col, dim_nome in [
        (COL_SEXO, "sexo"),
        ("faixa_etaria", "faixa_etaria"),
        (COL_COR, "cor_raca"),
        (COL_ESCOLARIDADE, "escolaridade"),
    ]:
        sub = _share_ponderado(df, [COL_UF, dim_col])
        sub = sub.rename(columns={dim_col: "valor"})
        sub.insert(1, "dimensao", dim_nome)
        blocos.append(sub)

    return pd.concat(blocos, ignore_index=True)


def perfil_economico(df_pnadc: pd.DataFrame) -> pd.DataFrame:
    """Renda média e mediana ponderada — por UF.

    (Jornada de trabalho fica como TODO: variável não harmonizada nesta versão.)
    """
    df = marcar_nano(df_pnadc)
    df = df[df["is_nano"]].copy()

    media = _media_ponderada(df, COL_RENDA, [COL_UF]).rename(
        columns={"media": "renda_mensal_media_brl"}
    )

    medianas = (
        df.groupby(COL_UF, observed=True)
        .apply(lambda g: _mediana_ponderada(
            g[COL_RENDA].fillna(0).to_numpy(),
            g[COL_PESO].to_numpy(),
        ), include_groups=False)
        .rename("renda_mensal_mediana_brl")
        .reset_index()
    )
    return media.merge(medianas, on=COL_UF)


def perfil_setorial(df_pnadc: pd.DataFrame) -> pd.DataFrame:
    """Distribuição por seção CNAE (A-U) — por UF.

    Útil para identificar onde se concentram setores aderentes ao modelo
    de venda direta da ABEVD (Comércio = G, Serviços pessoais = S).
    """
    df = marcar_nano(df_pnadc)
    df = df[df["is_nano"]].copy()
    return _share_ponderado(df, [COL_UF, COL_CNAE_SECAO]).rename(
        columns={COL_CNAE_SECAO: "cnae_secao"}
    )


def recorte_mulheres_comercio_servicos(df_pnadc: pd.DataFrame) -> pd.DataFrame:
    """**Recorte estratégico ABEVD**: nano-empreendedoras mulheres adultas
    (25-49 anos) em Comércio (G) e Outras atividades de serviços (S), por UF.

    Esse é o público naturalmente alinhado ao modelo de consultoras de venda
    direta — as estimativas aqui medem o tamanho do mercado-alvo de expansão.

    Returns:
        DataFrame com (uf, n_amostral, total_expandido, share_no_grupo_nano_pct).
    """
    df = marcar_nano(df_pnadc)
    df = df[df["is_nano"]].copy()

    cond = (
        df[COL_SEXO].eq("feminino")
        & df[COL_IDADE].between(25, 49)
        & df[COL_CNAE_SECAO].isin(["G", "S"])
    )

    alvo = df[cond]
    base_uf = (
        df.groupby(COL_UF, observed=True)[COL_PESO].sum()
        .rename("total_nano_uf_expandido").reset_index()
    )
    res = (
        alvo.groupby(COL_UF, observed=True)
        .agg(n_amostral=(COL_PESO, "size"),
             total_expandido=(COL_PESO, "sum"))
        .reset_index()
        .merge(base_uf, on=COL_UF, how="right")
        .fillna({"n_amostral": 0, "total_expandido": 0.0})
    )
    res["n_amostral"] = res["n_amostral"].astype(int)
    res["share_no_nano_uf_pct"] = (
        100 * res["total_expandido"] / res["total_nano_uf_expandido"]
    ).round(2)
    return res.sort_values("total_expandido", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Série temporal
# ---------------------------------------------------------------------------

def serie_temporal_perfis(
    pnadc_paths: list[tuple[Path, str]],
) -> dict[str, pd.DataFrame]:
    """Roda os 4 perfis para múltiplos trimestres da PNADC.

    Args:
        pnadc_paths: lista de tuplas (parquet_path, label_periodo).

    Returns:
        Dict com chaves: 'demografico', 'economico', 'setorial', 'recorte_abevd'.
        Cada DataFrame é a concatenação dos períodos com coluna ``periodo``.
    """
    blocos: dict[str, list[pd.DataFrame]] = {
        "demografico": [], "economico": [], "setorial": [], "recorte_abevd": [],
    }
    for path, label in pnadc_paths:
        logger.info("=== Perfis para período %s ===", label)
        df = carregar_pnadc_processado(path)
        for nome, fn in [
            ("demografico", perfil_demografico),
            ("economico", perfil_economico),
            ("setorial", perfil_setorial),
            ("recorte_abevd", recorte_mulheres_comercio_servicos),
        ]:
            sub = fn(df).copy()
            sub.insert(0, "periodo", label)
            blocos[nome].append(sub)
    return {k: pd.concat(v, ignore_index=True) for k, v in blocos.items()}


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def salvar_perfis(perfis: dict[str, pd.DataFrame], out_dir: Path) -> dict[str, Path]:
    """Salva cada perfil em CSV + parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths_out: dict[str, Path] = {}
    for nome, df in perfis.items():
        csv_path = out_dir / f"perfil_{nome}.csv"
        parquet_path = out_dir / f"perfil_{nome}.parquet"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        df.to_parquet(parquet_path, index=False)
        paths_out[nome] = csv_path
        logger.info("Salvo: %s + .parquet (%d linhas)", csv_path.name, len(df))
    return paths_out


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periodo", default=None,
                        help="rodar apenas 1 período; default: série 2025 completa")
    args = parser.parse_args()

    pnadc_paths = [
        (paths.DATA_PROCESSED / "PNADC_012025.parquet", "2025T1"),
        (paths.DATA_PROCESSED / "PNADC_022025.parquet", "2025T2"),
        (paths.DATA_PROCESSED / "PNADC_032025.parquet", "2025T3"),
        (paths.DATA_PROCESSED / "PNADC_042025.parquet", "2025T4"),
    ]
    if args.periodo:
        pnadc_paths = [p for p in pnadc_paths if p[1] == args.periodo]
        if not pnadc_paths:
            raise SystemExit(f"Período {args.periodo} não está nos pares default")

    perfis = serie_temporal_perfis(pnadc_paths)
    out_dir = paths.OUT_TABELAS / "etapa3"
    salvar_perfis(perfis, out_dir)


if __name__ == "__main__":
    main()

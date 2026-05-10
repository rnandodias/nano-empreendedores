"""Estimativa do universo de nano-empreendedores (Etapa 2).

Implementa o pipeline analítico:
1. Carrega PNADC processada (1 parquet por trimestre).
2. Aplica recorte da definição operacional (conta-própria com renda anual ≤ R$ 40 mil).
3. Expande pela amostra com pesos calibrados, respeitando o desenho complexo
   (estratos × UPAs) — variância via método de Taylor (samplics).
4. Cruza por UF (e opcionalmente por CNAE-seção × sexo × faixa etária) com o
   Cadastro MEI para estimar a fração formalizada.
5. Retorna estimativas por UF com IC 95% E versão empilhada para série temporal.

Saídas em ``outputs/tabelas/etapa2/``:
- ``nano_total_uf_<periodo>.csv`` — uma linha por UF
- ``nano_serie_temporal.csv`` — período × UF (longo)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src import paths
from src.transform.filters import is_nano_empreendedor

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Definição operacional (constantes)
# ---------------------------------------------------------------------------

COL_POSICAO = "posicao_ocupacao"
COL_RENDA = "renda_mensal_brl"
COL_PESO = "peso_amostral"
COL_UF = "uf"
COL_UPA = "upa"
COL_ESTRATO = "estrato"


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------

def carregar_pnadc_processado(path: Path) -> pd.DataFrame:
    """Lê o parquet PNADC harmonizado e valida colunas mínimas."""
    df = pd.read_parquet(path)
    obrigatorias = {COL_POSICAO, COL_RENDA, COL_PESO, COL_UF, COL_UPA, COL_ESTRATO}
    faltam = obrigatorias - set(df.columns)
    if faltam:
        raise ValueError(f"PNADC em {path} sem colunas obrigatórias: {faltam}")
    logger.info("PNADC carregada: %s — %d linhas", path.name, len(df))
    return df


def carregar_mei_processado(path: Path) -> pd.DataFrame:
    """Lê o parquet MEI ativos."""
    df = pd.read_parquet(path)
    if "mei_ativo" not in df.columns or "uf" not in df.columns:
        raise ValueError(f"MEI em {path} sem colunas mei_ativo/uf")
    logger.info("MEI carregado: %s — %d linhas", path.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Marcação da definição operacional
# ---------------------------------------------------------------------------

def marcar_nano(df_pnadc: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas booleanas: ``is_conta_propria`` e ``is_nano``."""
    df = df_pnadc.copy()
    df["is_conta_propria"] = df[COL_POSICAO].eq("conta_propria")
    df["is_nano"] = is_nano_empreendedor(df, COL_POSICAO, COL_RENDA).astype(bool)
    return df


# ---------------------------------------------------------------------------
# Estimativas com desenho amostral complexo (Taylor / samplics)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EstimativaUF:
    uf: str
    n_amostral: int
    n_amostral_cp: int           # n de conta-própria (denominador)
    n_amostral_nano: int         # n de nano-empreendedores (numerador)
    total_estimado: float        # nano-empreendedores expandidos
    total_cp_estimado: float     # todos os conta-própria expandidos
    share_nano_em_cp: float      # nano / conta-própria (%)
    ic95_low: float
    ic95_high: float
    cv_pct: float                # coeficiente de variação % (sanity)


def _estimar_total_taylor(
    df: pd.DataFrame,
    col_y: str,
    col_peso: str = COL_PESO,
    col_estrato: str = COL_ESTRATO,
    col_psu: str = COL_UPA,
    col_dominio: str = COL_UF,
) -> pd.DataFrame:
    """Estima total ponderado de ``col_y`` por ``col_dominio`` com variância de Taylor.

    Tenta usar ``samplics``. Se não disponível, faz fallback para estimativa
    pontual (sem IC) e loga warning.

    Returns:
        DataFrame com colunas: dominio, total, stderr, ic95_low, ic95_high, cv.
    """
    try:
        from samplics.estimation import TaylorEstimator
        from samplics.utils.types import PopParam, SinglePSUEst
    except ImportError:
        logger.warning("samplics não instalado — IC e CV ficarão NaN. "
                       "Instale com: pip install 'samplics<0.5'")
        return _estimar_total_simples(df, col_y, col_peso, col_dominio)

    # PNADC tem alguns estratos com 1 só UPA (RMs/RIDEs com 1 setor único).
    # Tratamos como "certainty" (variância 0 nesses estratos) — é a opção
    # padrão do IBGE em publicações que usam Taylor. Alternativas seriam
    # SinglePSUEst.combine (mais conservador) ou .skip (descarta esses
    # estratos). A escolha de "certainty" é registrada em ADR-008.
    est = TaylorEstimator(param=PopParam.total, alpha=0.05)
    est.estimate(
        y=df[col_y].to_numpy(),
        samp_weight=df[col_peso].to_numpy(),
        stratum=df[col_estrato].to_numpy(),
        psu=df[col_psu].to_numpy(),
        domain=df[col_dominio].to_numpy(),
        coef_var=True,
        remove_nan=True,
        single_psu=SinglePSUEst.certainty,
    )
    res = est.to_dataframe()
    # samplics 0.4.x devolve colunas em snake_case: _param, _domain,
    # _estimate, _stderror, _lci, _uci, _cv (CV em fração, não %)
    rename_map = {
        "_domain": col_dominio,
        "_estimate": "total",
        "_stderror": "stderr",
        "_lci": "ic95_low",
        "_uci": "ic95_high",
        "_cv": "cv",
    }
    res = res.rename(columns={k: v for k, v in rename_map.items() if k in res.columns})
    cols_out = [col_dominio, "total", "stderr", "ic95_low", "ic95_high", "cv"]
    return res[[c for c in cols_out if c in res.columns]]


def _estimar_total_simples(
    df: pd.DataFrame,
    col_y: str,
    col_peso: str,
    col_dominio: str,
) -> pd.DataFrame:
    """Fallback sem variância: apenas soma dos pesos."""
    g = df.groupby(col_dominio, observed=True)
    out = pd.DataFrame({
        "total": (df[col_y] * df[col_peso]).groupby(df[col_dominio], observed=True).sum(),
    }).reset_index()
    out["stderr"] = float("nan")
    out["ic95_low"] = float("nan")
    out["ic95_high"] = float("nan")
    out["cv"] = float("nan")
    return out


def estimar_universo_uf(df_pnadc: pd.DataFrame) -> pd.DataFrame:
    """Estima nano-empreendedores e conta-própria total por UF, com IC 95%.

    Args:
        df_pnadc: PNADC harmonizada (saída de ``carregar_pnadc_processado``).

    Returns:
        DataFrame com colunas:
          uf, n_amostral, n_amostral_cp, n_amostral_nano,
          total_cp_estimado, total_nano_estimado,
          ic95_low, ic95_high, cv_pct, share_nano_em_cp.
    """
    df = marcar_nano(df_pnadc)

    # Contagens amostrais (sem peso) por UF
    n_amostral = df.groupby(COL_UF, observed=True).size().rename("n_amostral")
    n_amostral_cp = (
        df[df["is_conta_propria"]]
        .groupby(COL_UF, observed=True).size().rename("n_amostral_cp")
    )
    n_amostral_nano = (
        df[df["is_nano"]]
        .groupby(COL_UF, observed=True).size().rename("n_amostral_nano")
    )

    # Estimadores ponderados com IC (Taylor)
    df_aux = df.assign(
        _y_cp=df["is_conta_propria"].astype(int),
        _y_nano=df["is_nano"].astype(int),
    )
    est_cp = _estimar_total_taylor(df_aux, "_y_cp").rename(
        columns={"total": "total_cp_estimado"}
    )[["uf", "total_cp_estimado"]]
    est_nano = _estimar_total_taylor(df_aux, "_y_nano").rename(
        columns={"total": "total_nano_estimado",
                 "ic95_low": "ic95_low",
                 "ic95_high": "ic95_high",
                 "cv": "cv_pct"},
    )[["uf", "total_nano_estimado", "ic95_low", "ic95_high", "cv_pct"]]

    # Junta tudo
    out = (
        pd.concat([n_amostral, n_amostral_cp, n_amostral_nano], axis=1)
        .reset_index()
        .merge(est_cp, on="uf", how="left")
        .merge(est_nano, on="uf", how="left")
    )
    out["n_amostral_cp"] = out["n_amostral_cp"].fillna(0).astype(int)
    out["n_amostral_nano"] = out["n_amostral_nano"].fillna(0).astype(int)
    out["share_nano_em_cp"] = (
        out["total_nano_estimado"] / out["total_cp_estimado"]
    ).round(4)
    out["cv_pct"] = (out["cv_pct"] * 100).round(2)
    return out.sort_values("total_nano_estimado", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Cruzamento com MEI (formal × informal)
# ---------------------------------------------------------------------------

def estimar_mei_ativo_por_uf(df_mei: pd.DataFrame) -> pd.DataFrame:
    """Conta MEI ativos por UF — não é amostra, é cadastro (sem IC)."""
    grp = (
        df_mei[df_mei["mei_ativo"]]
        .groupby("uf", observed=True).size()
        .rename("mei_ativos_total")
        .reset_index()
    )
    return grp


def cruzar_com_mei(
    estimativas_uf: pd.DataFrame,
    df_mei: pd.DataFrame,
) -> pd.DataFrame:
    """Adiciona à tabela de UF: MEI ativos, taxa de formalização, informais.

    **Importante:** o teto MEI vigente (~R$ 81 mil/ano) é maior que o teto nano
    (R$ 40 mil). Logo NEM TODO MEI é nano-empreendedor — uma fração dos MEI tem
    renda > 40 mil. Estimamos isso a partir da PNADC: dos conta-própria com
    renda > 40 mil, qual a fração que está formalizada como MEI? (No relatório
    técnico, registrar essa decisão como limitação.)

    Por ora, cálculo conservador:
      - mei_ativos_total: do cadastro MEI direto
      - taxa_formalizacao_aprox = min(mei_ativos / total_nano_estimado, 1.0)
      - informais_aprox = total_nano_estimado - min(mei_ativos, total_nano_estimado)

    Returns:
        ``estimativas_uf`` enriquecida com colunas: mei_ativos_total,
        taxa_formalizacao_aprox, informais_aprox, observacao_mei_>_nano.
    """
    mei_uf = estimar_mei_ativo_por_uf(df_mei)
    out = estimativas_uf.merge(mei_uf, on="uf", how="left")
    out["mei_ativos_total"] = out["mei_ativos_total"].fillna(0).astype(int)
    out["taxa_formalizacao_aprox"] = (
        out["mei_ativos_total"] / out["total_nano_estimado"]
    ).clip(upper=1.0).round(4)
    out["informais_aprox"] = (
        out["total_nano_estimado"] - out[["mei_ativos_total", "total_nano_estimado"]].min(axis=1)
    ).round(0)
    out["observacao_mei_maior_nano"] = (
        out["mei_ativos_total"] > out["total_nano_estimado"]
    )
    return out


# ---------------------------------------------------------------------------
# Série temporal
# ---------------------------------------------------------------------------

def serie_temporal(
    pares: list[tuple[Path, Path, str]],
) -> pd.DataFrame:
    """Estima e cruza para múltiplos períodos pareados (PNADC × MEI).

    Args:
        pares: lista de tuplas ``(pnadc_path, mei_path, label_periodo)``.

    Returns:
        DataFrame longo (um registro por período × UF) com todas as métricas.
    """
    quadros: list[pd.DataFrame] = []
    for pnadc_path, mei_path, label in pares:
        logger.info("=== Processando período %s ===", label)
        df_pnadc = carregar_pnadc_processado(pnadc_path)
        df_mei = carregar_mei_processado(mei_path)
        est = estimar_universo_uf(df_pnadc)
        est = cruzar_com_mei(est, df_mei)
        est.insert(0, "periodo", label)
        quadros.append(est)
    return pd.concat(quadros, ignore_index=True)


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def salvar_resultados(
    estimativas: pd.DataFrame,
    out_dir: Path,
    nome_base: str = "nano_total_uf",
) -> tuple[Path, Path]:
    """Salva tabela em CSV (utf-8-sig p/ Excel) e parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{nome_base}.csv"
    parquet_path = out_dir / f"{nome_base}.parquet"
    estimativas.to_csv(csv_path, index=False, encoding="utf-8-sig")
    estimativas.to_parquet(parquet_path, index=False)
    logger.info("Tabelas gravadas: %s, %s", csv_path.name, parquet_path.name)
    return csv_path, parquet_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolver_pares_default() -> list[tuple[Path, Path, str]]:
    """Pareamento canônico da série 2025: trimestre PNADC ↔ MEI fim do trimestre."""
    return [
        (paths.DATA_PROCESSED / "PNADC_012025.parquet",
         paths.DATA_PROCESSED / "mei_ativos_2025-03.parquet",
         "2025T1"),
        (paths.DATA_PROCESSED / "PNADC_022025.parquet",
         paths.DATA_PROCESSED / "mei_ativos_2025-06.parquet",
         "2025T2"),
        (paths.DATA_PROCESSED / "PNADC_032025.parquet",
         paths.DATA_PROCESSED / "mei_ativos_2025-09.parquet",
         "2025T3"),
        (paths.DATA_PROCESSED / "PNADC_042025.parquet",
         paths.DATA_PROCESSED / "mei_ativos_2025-12.parquet",
         "2025T4"),
    ]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periodo", default=None,
                        help="rodar apenas 1 período (ex.: 2025T4); default: série 2025 completa")
    args = parser.parse_args()

    pares = _resolver_pares_default()
    if args.periodo:
        pares = [p for p in pares if p[2] == args.periodo]
        if not pares:
            raise SystemExit(f"Período {args.periodo} não está nos pares default")

    df = serie_temporal(pares)
    out_dir = paths.OUT_TABELAS / "etapa2"
    salvar_resultados(df, out_dir, nome_base="nano_serie_temporal")

    # Print resumo Brasil + top-5 UFs do período mais recente
    print("\n=== RESUMO ===")
    for periodo in sorted(df["periodo"].unique()):
        sub = df[df["periodo"] == periodo]
        print(f"\n[{periodo}]")
        print(f"  Total Brasil estimado: {sub['total_nano_estimado'].sum():,.0f}")
        print(f"  Top 5 UFs:")
        for _, r in sub.nlargest(5, "total_nano_estimado").iterrows():
            print(f"    {r['uf']}: {r['total_nano_estimado']:>13,.0f}  "
                  f"IC95=[{r['ic95_low']:>13,.0f}, {r['ic95_high']:>13,.0f}]  "
                  f"MEI={r['mei_ativos_total']:>10,.0f}")


if __name__ == "__main__":
    main()

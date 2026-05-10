"""Gráficos do relatório técnico — matplotlib (export PNG estático).

Refatorado de Plotly+kaleido para matplotlib porque o kaleido travou
indefinidamente no ambiente Windows. Matplotlib gera PNG nativo, sem
dependências externas (browser, kaleido bundle).

Convenções:
- Paleta institucional sóbria definida em PALETA.
- DPI alto (200) para o PDF impresso.
- Backend "Agg" (sem GUI) — seguro para subprocess/scripts.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sem GUI; deve vir ANTES de pyplot

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Identidade visual
# ---------------------------------------------------------------------------

PALETA = {
    "primaria":   "#1B3A57",
    "secundaria": "#D9A441",
    "neutro":     "#6B7280",
    "destaque":   "#B0413E",
    "claro":      "#E5E7EB",
    "fundo":      "#FFFFFF",
}

# Padrão visual global
plt.rcParams.update({
    "font.family": "Helvetica" if "Helvetica" in plt.rcParams["font.family"] else "sans-serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlecolor": PALETA["primaria"],
    "axes.labelcolor": PALETA["primaria"],
    "axes.edgecolor": PALETA["claro"],
    "axes.grid": True,
    "grid.color": PALETA["claro"],
    "grid.linewidth": 0.5,
    "xtick.color": PALETA["neutro"],
    "ytick.color": PALETA["neutro"],
    "figure.facecolor": PALETA["fundo"],
    "axes.facecolor": PALETA["fundo"],
})

DPI = 200


def _salvar(fig, out_png: Path) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight", facecolor=PALETA["fundo"])
    plt.close(fig)
    logger.info("Gráfico salvo: %s", out_png.name)


def _formato_pt(v: float) -> str:
    """Formata número no padrão BR: 1.234.567"""
    return f"{int(v):,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def barras_top_uf(
    df: pd.DataFrame,
    col_uf: str,
    col_valor: str,
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,  # mantido para compat — ignorado
    top: int = 27,
    formato_valor: str = ",.0f",  # ignorado, usamos _formato_pt
    sub_titulo: str | None = None,
) -> None:
    """Barras horizontais por UF, ordenadas decrescentemente pela métrica."""
    sub = df.nlargest(top, col_valor).sort_values(col_valor)
    fig, ax = plt.subplots(figsize=(11, max(6, len(sub) * 0.32)))
    bars = ax.barh(sub[col_uf], sub[col_valor], color=PALETA["primaria"])
    for bar, val in zip(bars, sub[col_valor]):
        ax.text(bar.get_width() * 1.005, bar.get_y() + bar.get_height() / 2,
                _formato_pt(val), va="center", fontsize=9, color=PALETA["primaria"])
    ax.set_title(titulo, loc="left", pad=18)
    if sub_titulo:
        ax.text(0, 1.02, sub_titulo, transform=ax.transAxes,
                fontsize=10, color=PALETA["neutro"], style="italic")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: _formato_pt(x)))
    _salvar(fig, out_png)


def evolucao_temporal_brasil(
    df_serie: pd.DataFrame,
    col_periodo: str,
    series: list[tuple[str, str, str]],
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,
    sub_titulo: str | None = None,
    formato_y: str = ",.0f",
) -> None:
    """Linhas temporais para múltiplas séries."""
    periodos = sorted(df_serie[col_periodo].unique())
    fig, ax = plt.subplots(figsize=(11, 6))
    for col, label, cor in series:
        valores = [df_serie[df_serie[col_periodo] == p][col].sum() for p in periodos]
        ax.plot(periodos, valores, marker="o", linewidth=3, markersize=10,
                color=cor, label=label)
        for x, y in zip(periodos, valores):
            ax.annotate(_formato_pt(y), (x, y),
                        textcoords="offset points", xytext=(0, 12),
                        ha="center", fontsize=10, color=cor, fontweight="bold")
    ax.set_title(titulo, loc="left", pad=18)
    if sub_titulo:
        ax.text(0, 1.02, sub_titulo, transform=ax.transAxes,
                fontsize=10, color=PALETA["neutro"], style="italic")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=len(series),
              frameon=False, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: _formato_pt(x)))
    fig.subplots_adjust(bottom=0.2)
    _salvar(fig, out_png)


def barras_setor_cnae(
    df: pd.DataFrame,
    col_secao: str,
    col_valor: str,
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,
    top: int = 12,
    sub_titulo: str | None = None,
    destaques: tuple[str, ...] = ("G", "S"),
) -> None:
    """Barras por seção CNAE, com destaque para seções relevantes (G+S = ABEVD)."""
    sub = df.nlargest(top, col_valor).sort_values(col_valor)
    cores = [PALETA["destaque"] if s in destaques else PALETA["primaria"]
             for s in sub[col_secao]]
    fig, ax = plt.subplots(figsize=(11, max(5, len(sub) * 0.45)))
    bars = ax.barh(sub[col_secao], sub[col_valor], color=cores)
    for bar, val in zip(bars, sub[col_valor]):
        ax.text(bar.get_width() * 1.005, bar.get_y() + bar.get_height() / 2,
                _formato_pt(val), va="center", fontsize=10, color=PALETA["primaria"])
    ax.set_title(titulo, loc="left", pad=18)
    if sub_titulo:
        ax.text(0, 1.02, sub_titulo, transform=ax.transAxes,
                fontsize=10, color=PALETA["neutro"], style="italic")
    ax.set_xlabel("")
    ax.set_ylabel("Seção CNAE")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: _formato_pt(x)))
    _salvar(fig, out_png)


def piramide_etaria_simples(
    df_dem: pd.DataFrame,
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,
    sub_titulo: str | None = None,
) -> None:
    """Distribuição etária ponderada (faixas) — Brasil agregado."""
    sub = df_dem[df_dem["dimensao"] == "faixa_etaria"].copy()
    if sub.empty:
        logger.warning("Sem dados de faixa_etaria")
        return
    agg = sub.groupby("valor", observed=True)["total_expandido"].sum().reset_index()
    agg["share_pct"] = (100 * agg["total_expandido"] / agg["total_expandido"].sum()).round(1)
    ordem = ["jovem_14_24", "adulto_25_49", "maduro_50_mais"]
    rotulos = {"jovem_14_24": "14-24 anos",
               "adulto_25_49": "25-49 anos",
               "maduro_50_mais": "50+ anos"}
    agg["valor"] = pd.Categorical(agg["valor"], categories=ordem, ordered=True)
    agg = agg.sort_values("valor")
    cores = [PALETA["neutro"], PALETA["primaria"], PALETA["secundaria"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh([rotulos[v] for v in agg["valor"]], agg["share_pct"], color=cores)
    for bar, val in zip(bars, agg["share_pct"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val}%", va="center", fontsize=12,
                color=PALETA["primaria"], fontweight="bold")
    ax.set_title(titulo, loc="left", pad=18)
    if sub_titulo:
        ax.text(0, 1.02, sub_titulo, transform=ax.transAxes,
                fontsize=10, color=PALETA["neutro"], style="italic")
    ax.set_xlabel("% dentro do universo nano")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _salvar(fig, out_png)


def barras_pareadas_cp_mei(
    df: pd.DataFrame,
    col_uf: str = "uf",
    col_cp: str = "total_nano_estimado",
    col_mei: str = "mei_ativos_total",
    titulo: str = "Universo nano-empreendedor vs MEI ativos por UF",
    out_png: Path | None = None,
    out_html: Path | None = None,
    top: int = 15,
    sub_titulo: str | None = None,
) -> None:
    """Barras pareadas: nano (PNADC expandido) × MEI ativos (cadastro)."""
    sub = df.nlargest(top, col_cp).sort_values(col_cp)
    fig, ax = plt.subplots(figsize=(11, max(7, len(sub) * 0.45)))
    y = range(len(sub))
    h = 0.4
    ax.barh([yi - h / 2 for yi in y], sub[col_cp], height=h,
            color=PALETA["primaria"], label="Nano (PNADC)")
    ax.barh([yi + h / 2 for yi in y], sub[col_mei], height=h,
            color=PALETA["secundaria"], label="MEI ativo (cadastro)")
    ax.set_yticks(list(y))
    ax.set_yticklabels(sub[col_uf])
    ax.set_title(titulo, loc="left", pad=18)
    if sub_titulo:
        ax.text(0, 1.02, sub_titulo, transform=ax.transAxes,
                fontsize=10, color=PALETA["neutro"], style="italic")
    ax.legend(loc="lower right", frameon=False, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: _formato_pt(x)))
    _salvar(fig, out_png)


def barras_recorte_abevd(
    df_recorte: pd.DataFrame,
    titulo: str,
    out_png: Path,
    out_html: Path | None = None,
    top: int = 15,
    sub_titulo: str | None = None,
) -> None:
    """Top UFs no recorte estratégico ABEVD (mulheres 25-49 em G+S nano)."""
    barras_top_uf(
        df_recorte, "uf", "total_expandido",
        titulo=titulo, out_png=out_png,
        top=top, sub_titulo=sub_titulo,
    )

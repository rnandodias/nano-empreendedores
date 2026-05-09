"""Caminhos canônicos do projeto. Importe daqui em vez de hardcodar paths."""

from __future__ import annotations

from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]

DATA: Path = ROOT / "data"
DATA_RAW: Path = DATA / "raw"
DATA_INTERIM: Path = DATA / "interim"
DATA_PROCESSED: Path = DATA / "processed"

RAW_PNADC: Path = DATA_RAW / "pnadc"
RAW_CENSO: Path = DATA_RAW / "censo"
RAW_MEI: Path = DATA_RAW / "mei"

DOCS: Path = ROOT / "docs"

OUTPUTS: Path = ROOT / "outputs"
OUT_TABELAS: Path = OUTPUTS / "tabelas"
OUT_GRAFICOS: Path = OUTPUTS / "graficos"
OUT_RELATORIOS: Path = OUTPUTS / "relatorios"


def ensure_dirs() -> None:
    """Garante que todas as pastas canônicas existam."""
    for p in (
        DATA_RAW, DATA_INTERIM, DATA_PROCESSED,
        RAW_PNADC, RAW_CENSO, RAW_MEI,
        OUT_TABELAS, OUT_GRAFICOS, OUT_RELATORIOS,
    ):
        p.mkdir(parents=True, exist_ok=True)

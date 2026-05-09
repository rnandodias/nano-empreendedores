"""Ingestão dos microdados do Censo Demográfico (IBGE).

Fonte oficial:
    https://www.ibge.gov.br/estatisticas/sociais/trabalho/22827-censo-demografico-2022.html

Os microdados do Censo são pesados (vários GB por UF). O download é feito por UF para
permitir paralelização e retomada.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src import paths

UFS_BR = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]


def download(uf: str, tabela: str = "pessoas", force: bool = False) -> Path:
    """Baixa microdados do Censo para uma UF e tabela (pessoas | domicilios)."""
    raise NotImplementedError("TODO: download por UF com retomada")


def parse(arquivo_bruto: Path) -> Path:
    """Converte microdado bruto do Censo em parquet."""
    raise NotImplementedError("TODO: parser do layout do Censo")


def process_all(tabela: str = "pessoas") -> Path:
    """Concatena todas as UFs e gera o parquet final particionado por UF."""
    raise NotImplementedError("TODO: concat e particionamento")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf", default="todos", help="UF (sigla) ou 'todos'")
    parser.add_argument("--tabela", choices=["pessoas", "domicilios"], default="pessoas")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    paths.ensure_dirs()
    ufs = UFS_BR if args.uf == "todos" else [args.uf.upper()]
    for uf in ufs:
        bruto = download(uf, tabela=args.tabela, force=args.force)
        parse(bruto)
    final = process_all(tabela=args.tabela)
    print(f"Censo ({args.tabela}) processado: {final}")


if __name__ == "__main__":
    main()

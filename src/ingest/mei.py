"""Ingestão do Cadastro Nacional de Microempreendedores Individuais (MEI).

Fonte oficial:
    https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/dados-publicos-cnpj
    Dados Abertos CNPJ — extrair empresas com `simples_mei = 'S'` e situação ativa.

Variáveis de interesse:
    CNPJ, situação cadastral (ativo/inativo), data de início/baixa,
    CNAE principal, UF, município, porte (deve ser MEI).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src import paths


def download(periodo: str | None = None, force: bool = False) -> list[Path]:
    """Baixa dump CNPJ da Receita Federal (Empresas + Estabelecimentos + Simples).

    Args:
        periodo: 'YYYY-MM' do snapshot. Se None, usa o mais recente disponível.
    """
    raise NotImplementedError("TODO: download dos dumps CNPJ Dados Abertos RF")


def filter_mei(dumps_dir: Path) -> Path:
    """Filtra registros MEI ativos a partir dos dumps CNPJ.

    Returns:
        Caminho do parquet em data/processed/mei_ativos.parquet
    """
    raise NotImplementedError("TODO: join Empresas + Estabelecimentos + Simples e filtrar MEI ativos")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periodo", default=None, help="ex.: 2025-04 ou vazio para mais recente")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    paths.ensure_dirs()
    dumps = download(periodo=args.periodo, force=args.force)
    final = filter_mei(dumps[0].parent if dumps else paths.RAW_MEI)
    print(f"MEI processado: {final}")


if __name__ == "__main__":
    main()

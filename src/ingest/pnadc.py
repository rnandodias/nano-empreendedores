"""Ingestão da PNAD Contínua (microdados trimestrais, IBGE).

Fonte oficial:
    https://www.ibge.gov.br/estatisticas/sociais/trabalho/9171-pesquisa-nacional-por-amostra-de-domicilios-continua-mensal.html
    FTP: ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/

Variáveis de interesse iniciais (ver dicionário oficial PNADC):
    UF, V2007 (sexo), V2009 (idade), V2010 (cor/raça), VD3004 (escolaridade),
    VD4002 (condição de ocupação), VD4009 (posição na ocupação),
    VD4019 (rendimento mensal habitual de todos os trabalhos),
    V4010/V4013 (CNAE Domiciliar 2.0), V1028 (peso amostral),
    UPA (unidade primária de amostragem), Estrato.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src import paths


def download(trimestre: str, force: bool = False) -> Path:
    """Baixa o pacote da PNADC para um trimestre.

    Args:
        trimestre: string no formato 'YYYYQn', ex. '2024Q4'.
        force: se True, sobrescreve mesmo se já existir.

    Returns:
        Caminho do arquivo bruto baixado em data/raw/pnadc/.
    """
    raise NotImplementedError("TODO: implementar download via FTP IBGE com retomada e checagem de hash")


def parse(arquivo_bruto: Path) -> Path:
    """Converte o ZIP/TXT bruto da PNADC em parquet com tipos corretos.

    Returns:
        Caminho do parquet em data/interim/.
    """
    raise NotImplementedError("TODO: parser do layout fixo PNADC usando o dicionário oficial")


def process(parquet_interim: Path) -> Path:
    """Aplica padronização final: nomes harmonizados, derivações, encoding.

    Returns:
        Caminho do parquet final em data/processed/.
    """
    raise NotImplementedError("TODO: padronização e merge com codificações harmonizadas")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trimestre", required=True, help="ex.: 2024Q4")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    paths.ensure_dirs()
    bruto = download(args.trimestre, force=args.force)
    interim = parse(bruto)
    final = process(interim)
    print(f"PNADC {args.trimestre} processada: {final}")


if __name__ == "__main__":
    main()

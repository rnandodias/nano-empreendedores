"""Ingestão da PNAD Contínua (microdados trimestrais, IBGE).

Fonte oficial:
    https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/

O servidor migrou de FTP puro para HTTPS (mesmo path, host
``ftp.ibge.gov.br``). Esta tool usa HTTPS direto via ``requests``.

Variáveis de interesse iniciais (ver dicionário oficial PNADC):
    UF, V2007 (sexo), V2009 (idade), V2010 (cor/raça),
    VD3004 (escolaridade), VD4002 (condição de ocupação),
    VD4009 (posição na ocupação consolidada),
    VD4019 (rendimento mensal habitual de todos os trabalhos),
    V4010 (CNAE Domiciliar 2.0 — ocupação trab. principal),
    V4013 (atividade trab. principal — CNAE Domiciliar 2.0),
    V1028 (peso amostral calibrado), UPA, Estrato.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from src import paths
from src.transform import harmonize

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Constantes / endpoints
# ---------------------------------------------------------------------------

BASE_URL = (
    "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/"
    "Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/"
)
DOC_URL = BASE_URL + "Documentacao/"
DICIONARIO_ZIP_URL = DOC_URL + "Dicionario_e_input_20221031.zip"

# Subset de variáveis carregadas para análise. Nem tudo é necessário e o ZIP
# contém ~420 colunas — restringir economiza memória e tempo.
VARIAVEIS_ALVO: tuple[str, ...] = (
    # Identificação / desenho amostral
    "Ano", "Trimestre", "UF", "Capital", "RM_RIDE",
    "UPA", "Estrato", "V1008", "V1014", "V1016",
    "V1022", "V1023",
    "V1027", "V1028", "V1029", "V1033",
    "posest", "posest_sxi",
    "V2003",  # nº de ordem da pessoa
    # Demografia
    "V2007", "V2009", "V2010",
    # Trabalho — variáveis brutas e códigos CNAE/Ocupação
    "V4010", "V4012", "V4013", "V40132", "V40132A",
    # Variáveis derivadas (VD*)
    "VD3004",                  # escolaridade
    "VD4001", "VD4002",        # condição na força de trabalho / ocupação
    "VD4009",                  # posição na ocupação consolidada
    "VD4010", "VD4011",        # grupamentos
    "VD4016", "VD4017",        # rendimentos (efetivo / habitual trab. principal)
    "VD4019", "VD4020",        # rendimentos de todos os trabalhos (habitual / efetivo)
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trim_to_arquivo(trimestre: str) -> tuple[int, int]:
    """Converte 'YYYYQn' -> (trimestre_int, ano_int)."""
    m = re.fullmatch(r"(\d{4})Q([1-4])", trimestre)
    if not m:
        raise ValueError(f"Trimestre inválido: {trimestre!r}. Use formato 'YYYYQn'.")
    ano = int(m.group(1))
    trim = int(m.group(2))
    return trim, ano


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while buf := f.read(chunk):
            h.update(buf)
    return h.hexdigest()


def _http_get(url: str, dest: Path, force: bool = False) -> Path:
    """Download HTTP com barra de progresso, idempotente por presença + hash."""
    if dest.exists() and not force:
        logger.info("Já existe, pulando download: %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
        return dest

    logger.info("Baixando %s -> %s", url, dest)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=dest.name, leave=False
        ) as pbar:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        tmp.replace(dest)
    logger.info("Download concluído: %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest


def _listar_arquivos_remotos(ano: int) -> list[str]:
    """Lê o índice HTML do diretório do ano e retorna nomes de arquivos."""
    url = f"{BASE_URL}{ano}/"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return re.findall(r'href="(PNADC_[0-9_]+\.zip)"', r.text)


def _resolver_url_trimestre(trimestre: str) -> tuple[str, str, str]:
    """Retorna (trimestre_efetivo, url, nome_arquivo).

    Aplica fallback automático: se ``trimestre`` não estiver disponível ainda,
    desce para o trimestre anterior. Loga a substituição.
    """
    pedido = trimestre
    while True:
        trim, ano = _trim_to_arquivo(pedido)
        try:
            disponiveis = _listar_arquivos_remotos(ano)
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                disponiveis = []
            else:
                raise

        prefixo = f"PNADC_{trim:02d}{ano}"
        candidatos = [n for n in disponiveis if n.startswith(prefixo)]
        if candidatos:
            # nome pode vir com sufixo de data (PNADC_022024_20260324.zip) ou simples.
            # Se mais de um, pega o lexicograficamente maior (revisão mais recente).
            nome = sorted(candidatos)[-1]
            url = f"{BASE_URL}{ano}/{nome}"
            if pedido != trimestre:
                logger.warning(
                    "Fallback automático: %s não disponível. Usando %s (%s).",
                    trimestre, pedido, nome,
                )
            return pedido, url, nome

        # Não achou — recua um trimestre
        if trim == 1:
            ano_ant, trim_ant = ano - 1, 4
        else:
            ano_ant, trim_ant = ano, trim - 1
        if ano_ant < 2012:
            raise RuntimeError(
                f"Nenhum trimestre PNADC encontrado descendo a partir de {trimestre}."
            )
        logger.info("Trimestre %s não publicado ainda; tentando %d Q%d.", pedido, ano_ant, trim_ant)
        pedido = f"{ano_ant}Q{trim_ant}"


def _carregar_layout() -> pd.DataFrame:
    """Lê o input SAS oficial e retorna DataFrame com (nome, inicio, tamanho, tipo)."""
    sas_path = paths.RAW_PNADC / "input_PNADC_trimestral.sas"
    if not sas_path.exists():
        # Garante que o dicionário foi baixado e extraído.
        zip_path = paths.RAW_PNADC / "Dicionario_e_input_20221031.zip"
        _http_get(DICIONARIO_ZIP_URL, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(paths.RAW_PNADC)

    texto = sas_path.read_text(encoding="latin-1")
    # Padrão: @POS NOME [$]LARGURA.
    pat = re.compile(r"@(\d+)\s+(\w+)\s+(\$)?(\d+)\.")
    rows = []
    for inicio, nome, dollar, larg in pat.findall(texto):
        rows.append({
            "nome": nome,
            "inicio": int(inicio),         # 1-based, posição inicial
            "tamanho": int(larg),
            "tipo": "string" if dollar else "numeric",
        })
    df = pd.DataFrame(rows).drop_duplicates(subset=["nome"], keep="first")
    if df.empty:
        raise RuntimeError(f"Não consegui parsear o layout SAS em {sas_path}.")
    return df


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def _garantir_dicionario() -> None:
    """Baixa e extrai o dicionário/input SAS da PNADC (1x, idempotente)."""
    from src.ingest._http import DownloadItem, download_one

    paths.ensure_dirs()
    dicionario_zip = paths.RAW_PNADC / "Dicionario_e_input_20221031.zip"
    download_one(DownloadItem(url=DICIONARIO_ZIP_URL, dest=dicionario_zip))
    sas_input = paths.RAW_PNADC / "input_PNADC_trimestral.sas"
    if not sas_input.exists():
        with zipfile.ZipFile(dicionario_zip) as zf:
            zf.extractall(paths.RAW_PNADC)


def download(trimestre: str, force: bool = False) -> Path:
    """Baixa o pacote da PNADC para um trimestre, com resiliência.

    Usa ``_http.download_one`` (Range resumption + read timeout + retry).

    Args:
        trimestre: string no formato 'YYYYQn', ex. '2025Q4'.
        force: se True, sobrescreve mesmo se já existir.

    Returns:
        Caminho do arquivo bruto baixado em data/raw/pnadc/.
    """
    from src.ingest._http import DownloadItem, download_one

    _garantir_dicionario()
    trim_eff, url, nome = _resolver_url_trimestre(trimestre)
    dest = paths.RAW_PNADC / nome
    download_one(
        DownloadItem(
            url=url, dest=dest,
            meta_extra={
                "trimestre_solicitado": trimestre,
                "trimestre_efetivo": trim_eff,
            },
        ),
        force=force,
    )
    return dest


def download_trimestres(
    trimestres: list[str],
    force: bool = False,
    max_workers: int = 4,
) -> list[Path]:
    """Baixa múltiplos trimestres da PNADC em paralelo."""
    from src.ingest._http import DownloadItem, download_many

    _garantir_dicionario()
    items: list[DownloadItem] = []
    for trim in trimestres:
        trim_eff, url, nome = _resolver_url_trimestre(trim)
        items.append(DownloadItem(
            url=url,
            dest=paths.RAW_PNADC / nome,
            meta_extra={
                "trimestre_solicitado": trim,
                "trimestre_efetivo": trim_eff,
            },
        ))
    return download_many(items, max_workers=max_workers, force=force)


def parse(arquivo_bruto: Path) -> Path:
    """Converte o ZIP/TXT bruto da PNADC em parquet com tipos corretos.

    Lê apenas o subset declarado em :data:`VARIAVEIS_ALVO` para evitar carregar
    400+ colunas em memória.

    Returns:
        Caminho do parquet em data/interim/.
    """
    arquivo_bruto = Path(arquivo_bruto)
    layout = _carregar_layout()
    layout_alvo = layout[layout["nome"].isin(VARIAVEIS_ALVO)].copy()
    faltando = set(VARIAVEIS_ALVO) - set(layout_alvo["nome"])
    if faltando:
        logger.warning("Variáveis não encontradas no layout SAS: %s", sorted(faltando))

    # pandas.read_fwf usa colspecs 0-based, half-open: [inicio-1, inicio-1+tamanho)
    layout_alvo = layout_alvo.sort_values("inicio").reset_index(drop=True)
    colspecs = [(int(r.inicio) - 1, int(r.inicio) - 1 + int(r.tamanho)) for r in layout_alvo.itertuples()]
    nomes = layout_alvo["nome"].tolist()
    tipos = dict(zip(nomes, layout_alvo["tipo"]))

    # Identifica o TXT dentro do ZIP.
    with zipfile.ZipFile(arquivo_bruto) as zf:
        txts = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not txts:
            raise RuntimeError(f"Nenhum .txt dentro de {arquivo_bruto.name}.")
        if len(txts) > 1:
            logger.warning("Múltiplos .txt no ZIP, usando %s", txts[0])
        txt_nome = txts[0]
        logger.info("Lendo layout fixo de %s (%s) — %d colunas", arquivo_bruto.name, txt_nome, len(nomes))
        with zf.open(txt_nome) as fh:
            df = pd.read_fwf(
                fh,
                colspecs=colspecs,
                names=nomes,
                dtype=str,            # lê tudo como string e converte depois
                encoding="latin-1",
                na_values=["", " "],
                keep_default_na=False,
            )

    # Converte numéricos.
    for col, tp in tipos.items():
        if tp == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info("Parsing concluído: %d linhas × %d colunas", len(df), df.shape[1])

    # Identificador único de pessoa: UPA + V1008 + V1014 + V2003 (padrão PNADC).
    if all(c in df.columns for c in ("UPA", "V1008", "V1014", "V2003")):
        df["id_pessoa"] = (
            df["UPA"].astype(str).str.zfill(9)
            + df["V1008"].astype(str).str.zfill(2)
            + df["V1014"].astype(str).str.zfill(2)
            + df["V2003"].astype(str).str.zfill(2)
        )
    if all(c in df.columns for c in ("UPA", "V1008", "V1014")):
        df["id_domicilio"] = (
            df["UPA"].astype(str).str.zfill(9)
            + df["V1008"].astype(str).str.zfill(2)
            + df["V1014"].astype(str).str.zfill(2)
        )

    # Persiste em data/interim/
    nome_base = arquivo_bruto.stem  # ex: PNADC_042025
    out = paths.DATA_INTERIM / f"{nome_base}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    logger.info("Parquet interim gerado: %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


def _uf_codigo_para_sigla(serie: pd.Series) -> pd.Series:
    """Converte código IBGE de UF (string '11'..'53') para sigla."""
    mapa = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
        "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
        "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS",
        "50": "MS", "51": "MT", "52": "GO", "53": "DF",
    }
    return serie.astype(str).str.zfill(2).map(mapa).astype("category")


def process(parquet_interim: Path) -> Path:
    """Aplica padronização final: nomes harmonizados, derivações, encoding.

    Returns:
        Caminho do parquet final em data/processed/.
    """
    parquet_interim = Path(parquet_interim)
    df = pd.read_parquet(parquet_interim)
    logger.info("Carregado interim: %d linhas", len(df))

    # Harmonizações categóricas
    df = harmonize.harmonize_cor_raca(df, col="V2010", fonte="pnadc")
    df = harmonize.harmonize_escolaridade(df, col="VD3004", fonte="pnadc")
    df = harmonize.harmonize_posicao_ocupacao(df, col="VD4009", fonte="pnadc")

    # Renomeações e derivações
    out = pd.DataFrame()
    out["uf"] = _uf_codigo_para_sigla(df["UF"])
    out["sexo"] = df["V2007"].astype(str).map({"1": "masculino", "2": "feminino"}).astype("category")
    out["idade_anos"] = pd.to_numeric(df["V2009"], errors="coerce").astype("Int16")
    out["cor_raca"] = df["cor_raca"]
    out["escolaridade"] = df["escolaridade"]
    out["posicao_ocupacao"] = df["posicao_ocupacao"]
    out["renda_mensal_brl"] = pd.to_numeric(df["VD4019"], errors="coerce")
    out["renda_anual_brl"] = out["renda_mensal_brl"].fillna(0) * 12
    out["cnae_classe"] = df.get("V4013", pd.Series([None] * len(df))).astype("string")
    # V40132 (seção CNAE como letra) costumava vir preenchido em microdados
    # antigos, mas em PNADC 2025 o IBGE entrega vazio. Derivamos a seção a
    # partir das primeiras 2 posições de V4013 (divisão CNAE 2.0) usando a
    # tabela divisão→seção definida em src/ingest/mei.py::CNAE_DIVISAO_TO_SECAO.
    from src.ingest.mei import cnae_para_secao
    out["cnae_secao"] = (
        out["cnae_classe"].map(cnae_para_secao).astype("category")
    )

    # Pesos e desenho amostral — preservados na base processada (Etapa 2).
    out["peso_amostral"] = pd.to_numeric(df["V1028"], errors="coerce")
    out["upa"] = pd.to_numeric(df["UPA"], errors="coerce").astype("Int64")
    out["estrato"] = pd.to_numeric(df["Estrato"], errors="coerce").astype("Int64")

    # IDs e metadados auxiliares
    out["ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int16")
    out["trimestre"] = pd.to_numeric(df["Trimestre"], errors="coerce").astype("Int8")
    if "id_pessoa" in df:
        out["id_pessoa"] = df["id_pessoa"].astype("string")
    if "id_domicilio" in df:
        out["id_domicilio"] = df["id_domicilio"].astype("string")

    # Persistência
    nome_base = parquet_interim.stem  # PNADC_042025
    final_path = paths.DATA_PROCESSED / f"{nome_base}.parquet"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(final_path, index=False)
    logger.info("Parquet processed gerado: %s (%.1f MB)", final_path, final_path.stat().st_size / 1e6)

    # Sanity checks
    soma_pesos = float(out["peso_amostral"].sum())
    n_conta_propria = int((out["posicao_ocupacao"] == "conta_propria").sum())
    pop_estimada = float(out.loc[out["peso_amostral"].notna(), "peso_amostral"].sum())
    pessoas_com_renda = int((out["renda_mensal_brl"].fillna(0) > 0).sum())
    logger.info("n=%d  soma_pesos=%.0f (~população)  conta_propria=%d  com_renda>0=%d",
                len(out), soma_pesos, n_conta_propria, pessoas_com_renda)

    # Metadados acompanhantes
    meta = {
        "n_linhas": int(len(out)),
        "soma_pesos_amostrais": pop_estimada,
        "n_conta_propria": n_conta_propria,
        "n_renda_positiva": pessoas_com_renda,
        "colunas": list(out.columns),
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origem_interim": str(parquet_interim.relative_to(paths.ROOT)),
    }
    final_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--trimestre", help="ex.: 2025Q4")
    grp.add_argument("--trimestres",
                     help="lista separada por vírgula, ex.: 2025Q1,2025Q2,2025Q3,2025Q4")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4,
                        help="downloads simultâneos quando usar --trimestres (default 4)")
    parser.add_argument("--skip-download", action="store_true",
                        help="usa apenas ZIPs já presentes em data/raw/pnadc/")
    args = parser.parse_args()

    if args.trimestres:
        trimestres = [t.strip() for t in args.trimestres.split(",") if t.strip()]
    else:
        trimestres = [args.trimestre]

    paths.ensure_dirs()
    if not args.skip_download:
        if len(trimestres) == 1:
            download(trimestres[0], force=args.force)
        else:
            logger.info("Baixando %d trimestres em paralelo: %s",
                        len(trimestres), ", ".join(trimestres))
            download_trimestres(trimestres, force=args.force, max_workers=args.max_workers)

    finais: list[Path] = []
    for trim in trimestres:
        # Resolve nome de arquivo do trimestre (mesmo path resolver do download)
        _, _, nome = _resolver_url_trimestre(trim)
        bruto = paths.RAW_PNADC / nome
        if not bruto.exists():
            raise SystemExit(f"{bruto} não existe — rode o download primeiro.")
        interim = parse(bruto)
        finais.append(process(interim))

    print("PNADC processada:")
    for f in finais:
        print(f"  - {f}")


if __name__ == "__main__":
    main()

"""Ingestão do Cadastro Nacional de Microempreendedores Individuais (MEI).

A partir de janeiro/2026 a Receita Federal migrou os Dados Abertos CNPJ
para um Nextcloud público. NÃO usar URLs antigas
(``https://arquivos.receitafederal.gov.br/dados/cnpj/...``) — retornam 404.

Endpoint canônico (validado em 2026-05-09):

    Landing (humano, navegador):
        https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9
    Pasta de um snapshot mensal:
        https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9?dir=/<YYYY-MM>
    Download programático (WebDAV público):
        https://arquivos.receitafederal.gov.br/public.php/webdav/<YYYY-MM>/<arquivo>.zip
        Basic Auth: usuário = "YggdBLfdninEJX9" (share token), senha = vazia.

Dicionário/metadados oficial:
    https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf

Estrutura por snapshot (canônico desde 2021):
    Empresas{0..9}.zip          ~500 MB cada  (não baixado — não necessário)
    Estabelecimentos{0..9}.zip  ~2 GB / 350 MB cada  (UF, município, CNAE, situação)
    Socios{0..9}.zip            (não usados aqui)
    Simples.zip                 ~280 MB       (opção MEI: opcao_mei == 'S')
    Cnaes.zip, Municipios.zip, Motivos.zip, Naturezas.zip, Paises.zip,
    Qualificacoes.zip — tabelas auxiliares (KB).

CSVs vêm encoding latin-1, separador ';', SEM cabeçalho (ver PDF de
metadados para o layout de cada arquivo).

Estratégia para isolar MEI ativo (4 passos):
    1. Simples.zip → filtrar opcao_mei='S' e data_exclusao_mei=='0'/vazia
       → conjunto de cnpj_basico que são MEI vigentes.
    2. Estabelecimentos*.zip → filtrar identificador_matriz_filial='1' (matriz)
       E presença na lista MEI (cnpj_basico) → uf, município, CNAE, datas, situação.
    3. Empresas*.zip NÃO necessário para os recortes da Etapa 2 (UF × CNAE × estrato).
    4. Tabelas auxiliares (Municipios.zip) para enriquecer com código IBGE.

Variáveis de interesse no parquet final:
    cnpj_basico, cnpj_completo, situação cadastral (ativo/inativo),
    data de início de atividade, data de opção MEI,
    CNAE principal (código + seção), UF, município (cód. RFB → IBGE), mei_ativo (bool).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from tqdm import tqdm

from src import paths

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Constantes / endpoints
# ---------------------------------------------------------------------------

WEBDAV_BASE = "https://arquivos.receitafederal.gov.br/public.php/webdav"
SHARE_TOKEN = "YggdBLfdninEJX9"  # share público dos Dados Abertos CNPJ
AUTH = (SHARE_TOKEN, "")

DEFAULT_PERIODO = "2026-04"

# Arquivos a baixar (NÃO inclui Empresas*.zip — desnecessário para Etapa 2).
ARQUIVOS_ALVO: tuple[str, ...] = (
    "Simples.zip",
    "Cnaes.zip",
    "Municipios.zip",
    *[f"Estabelecimentos{i}.zip" for i in range(10)],
)

# ---------------------------------------------------------------------------
# Layouts (do PDF cnpj-metadados.pdf da Receita Federal)
# ---------------------------------------------------------------------------

# Simples.zip — colunas (ordem do CSV oficial RFB):
SIMPLES_COLS: tuple[str, ...] = (
    "cnpj_basico",
    "opcao_simples",
    "data_opcao_simples",
    "data_exclusao_simples",
    "opcao_mei",
    "data_opcao_mei",
    "data_exclusao_mei",
)

# Estabelecimentos*.zip — colunas (30 colunas, ordem oficial RFB):
ESTAB_COLS: tuple[str, ...] = (
    "cnpj_basico",                  # 0
    "cnpj_ordem",                   # 1
    "cnpj_dv",                      # 2
    "identificador_matriz_filial",  # 3  ('1'=matriz, '2'=filial)
    "nome_fantasia",                # 4
    "situacao_cadastral",           # 5  ('01' nula, '02' ativa, '03' suspensa, '04' inapta, '08' baixada)
    "data_situacao_cadastral",      # 6
    "motivo_situacao_cadastral",    # 7
    "nome_cidade_exterior",         # 8
    "pais",                         # 9
    "data_inicio_atividade",        # 10
    "cnae_fiscal_principal",        # 11
    "cnae_fiscal_secundaria",       # 12
    "tipo_logradouro",              # 13
    "logradouro",                   # 14
    "numero",                       # 15
    "complemento",                  # 16
    "bairro",                       # 17
    "cep",                          # 18
    "uf",                           # 19
    "municipio",                    # 20  (código RFB de 4 dígitos)
    "ddd_1",                        # 21
    "telefone_1",                   # 22
    "ddd_2",                        # 23
    "telefone_2",                   # 24
    "ddd_fax",                      # 25
    "fax",                          # 26
    "correio_eletronico",           # 27
    "situacao_especial",            # 28
    "data_situacao_especial",       # 29
)

# Subset que efetivamente persistimos em memória (resto é descartado).
ESTAB_USECOLS: tuple[str, ...] = (
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
    "identificador_matriz_filial",
    "situacao_cadastral",
    "data_situacao_cadastral",
    "data_inicio_atividade",
    "cnae_fiscal_principal",
    "uf",
    "municipio",
)

# Municipios.zip — código RFB ; nome
MUNIC_COLS: tuple[str, ...] = ("municipio_codigo_rfb", "municipio_nome")

# Cnaes.zip — código (7 díg., classe-CNAE 2.x) ; descrição
CNAES_COLS: tuple[str, ...] = ("cnae_codigo", "cnae_descricao")

# Mapeamento CNAE Classe (5 primeiros dígitos do CNAE 7-dig) → Seção CNAE 2.x.
# Tabela inline (faixas oficiais de divisões → seção, IBGE/CONCLA CNAE 2.0/2.3).
# Cada tupla (div_inicio, div_fim, secao). Divisão = primeiros 2 dígitos do CNAE.
CNAE_DIVISAO_TO_SECAO: tuple[tuple[int, int, str], ...] = (
    (1, 3, "A"),    # Agricultura, pecuária, produção florestal, pesca e aquicultura
    (5, 9, "B"),    # Indústrias extrativas
    (10, 33, "C"),  # Indústrias de transformação
    (35, 35, "D"),  # Eletricidade e gás
    (36, 39, "E"),  # Água, esgoto, gestão de resíduos e descontaminação
    (41, 43, "F"),  # Construção
    (45, 47, "G"),  # Comércio; reparação de veículos automotores e motocicletas
    (49, 53, "H"),  # Transporte, armazenagem e correio
    (55, 56, "I"),  # Alojamento e alimentação
    (58, 63, "J"),  # Informação e comunicação
    (64, 66, "K"),  # Atividades financeiras, de seguros e serviços relacionados
    (68, 68, "L"),  # Atividades imobiliárias
    (69, 75, "M"),  # Atividades profissionais, científicas e técnicas
    (77, 82, "N"),  # Atividades administrativas e serviços complementares
    (84, 84, "O"),  # Administração pública, defesa e seguridade social
    (85, 85, "P"),  # Educação
    (86, 88, "Q"),  # Saúde humana e serviços sociais
    (90, 93, "R"),  # Artes, cultura, esporte e recreação
    (94, 96, "S"),  # Outras atividades de serviços
    (97, 97, "T"),  # Serviços domésticos
    (99, 99, "U"),  # Organismos internacionais
)


def cnae_para_secao(cnae: str | None) -> str | None:
    """Devolve a letra da seção CNAE (A-U) a partir do código (5 ou 7 dígitos)."""
    if cnae is None or cnae == "" or pd.isna(cnae):
        return None
    s = str(cnae).strip()
    if not s.isdigit() or len(s) < 2:
        return None
    div = int(s[:2])
    for ini, fim, sec in CNAE_DIVISAO_TO_SECAO:
        if ini <= div <= fim:
            return sec
    return None


# ---------------------------------------------------------------------------
# Mapeamento município RFB → IBGE
# ---------------------------------------------------------------------------
# Os códigos de município no dump CNPJ usam a tabela TOM (Tabela de Órgãos
# Municipais) da RFB — 4 dígitos. O IBGE usa 7 dígitos. A ponte é feita via
# nome do município + UF, mas a abordagem mais robusta é via tabela de-para
# pública (o site dadosabertos.rfb / repositórios públicos publicam o
# de-para). Para esta primeira rodada NÃO tentamos resolver IBGE (deixamos
# `municipio_codigo_ibge` como None) — o código RFB já é suficiente para os
# recortes UF × Município × CNAE da Etapa 2. Iteração futura pode integrar
# tabela de-para.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while buf := f.read(chunk):
            h.update(buf)
    return h.hexdigest()


# Defaults de robustez de rede (ajustáveis via download(timeout_*=...))
_CONNECT_TIMEOUT_S = 30
_READ_TIMEOUT_S = 60     # se o server ficar 60s sem mandar bytes, dispara timeout
_MAX_TENTATIVAS = 8
_BACKOFF_BASE_S = 5


def _make_session() -> requests.Session:
    """Sessão HTTP com adaptador robusto: keepalive + retry de conexão."""
    s = requests.Session()
    s.auth = AUTH
    # Keepalive vem por padrão em requests; explicitar no header é opcional.
    s.headers.update({"Connection": "keep-alive", "Accept-Encoding": "identity"})
    return s


def _http_download(url: str, dest: Path, force: bool = False) -> Path:
    """Download HTTP idempotente com retomada (Range), read-timeout por chunk e retry.

    Estratégia:
    - Se ``dest`` já existe → pula (a menos que ``force=True``).
    - Senão, escreve em ``dest.part`` e sobe via ``Range: bytes=N-`` em cada
      retomada após erro de rede. Os bytes já em disco são preservados.
    - O ``read_timeout`` é por chunk: se o servidor engasgar > 60s sem mandar
      dados, o ``iter_content`` levanta exceção e entramos no retry.
    - Até ``_MAX_TENTATIVAS`` com backoff exponencial.
    """
    if dest.exists() and not force:
        logger.info(
            "Já existe, pulando download: %s (%.1f MB)",
            dest.name, dest.stat().st_size / 1e6,
        )
        return dest

    tmp = dest.with_suffix(dest.suffix + ".part")
    sess = _make_session()
    tentativa = 0
    while True:
        tentativa += 1
        ja_baixado = tmp.stat().st_size if tmp.exists() else 0
        headers: dict[str, str] = {}
        if ja_baixado > 0:
            headers["Range"] = f"bytes={ja_baixado}-"
            logger.info(
                "Retomada %s a partir de %.1f MB (tentativa %d/%d)",
                dest.name, ja_baixado / 1e6, tentativa, _MAX_TENTATIVAS,
            )
        else:
            logger.info(
                "Baixando %s (tentativa %d/%d) -> %s",
                url, tentativa, _MAX_TENTATIVAS, dest,
            )

        try:
            with sess.get(
                url, headers=headers, stream=True,
                timeout=(_CONNECT_TIMEOUT_S, _READ_TIMEOUT_S),
            ) as r:
                # 206 Partial Content é sucesso quando enviamos Range.
                # 200 OK é sucesso normal (servidor ignorou Range).
                if r.status_code == 200 and ja_baixado > 0:
                    # Servidor não suportou Range → reinicia do zero.
                    logger.warning(
                        "Servidor ignorou Range; reiniciando %s do zero",
                        dest.name,
                    )
                    tmp.unlink(missing_ok=True)
                    ja_baixado = 0
                r.raise_for_status()

                total_resto = int(r.headers.get("Content-Length", 0))
                total_final = ja_baixado + total_resto
                modo = "ab" if ja_baixado > 0 else "wb"
                with tmp.open(modo) as f, tqdm(
                    total=total_final,
                    initial=ja_baixado,
                    unit="B", unit_scale=True,
                    desc=dest.name, leave=False,
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            tmp.replace(dest)
            logger.info(
                "Download concluído: %s (%.1f MB)",
                dest.name, dest.stat().st_size / 1e6,
            )
            return dest

        except (requests.exceptions.RequestException, OSError) as exc:
            if tentativa >= _MAX_TENTATIVAS:
                logger.error(
                    "Falha definitiva em %s após %d tentativas: %s",
                    dest.name, tentativa, exc,
                )
                raise
            espera = _BACKOFF_BASE_S * (2 ** (tentativa - 1))
            logger.warning(
                "Erro em %s (tentativa %d): %s — retomando em %ds",
                dest.name, tentativa, exc, espera,
            )
            import time
            time.sleep(espera)


def _write_meta(dest: Path, url: str, periodo: str) -> None:
    meta = {
        "url": url,
        "arquivo": dest.name,
        "periodo": periodo,
        "tamanho_bytes": dest.stat().st_size,
        "sha256": _sha256(dest),
        "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    dest.with_suffix(dest.suffix + ".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# API pública: download
# ---------------------------------------------------------------------------

def download(periodo: str = DEFAULT_PERIODO, force: bool = False) -> list[Path]:
    """Baixa o snapshot CNPJ Dados Abertos para um período (YYYY-MM).

    Não baixa Empresas*.zip — não são necessários para os recortes da Etapa 2.

    Args:
        periodo: 'YYYY-MM' do snapshot (default: 2026-04, validado).
        force: sobrescreve mesmo se já existir.

    Returns:
        Lista de caminhos baixados em data/raw/mei/<periodo>/.
    """
    paths.ensure_dirs()
    dest_dir = paths.RAW_MEI / periodo
    dest_dir.mkdir(parents=True, exist_ok=True)

    baixados: list[Path] = []
    for nome in ARQUIVOS_ALVO:
        url = f"{WEBDAV_BASE}/{periodo}/{nome}"
        dest = dest_dir / nome
        existed = dest.exists()
        _http_download(url, dest, force=force)
        # Recalcula meta se o download ocorreu OU se .meta.json não existe.
        meta_path = dest.with_suffix(dest.suffix + ".meta.json")
        if (not existed) or force or (not meta_path.exists()):
            _write_meta(dest, url, periodo)
        baixados.append(dest)
    return baixados


# ---------------------------------------------------------------------------
# Leitura de CSVs dentro dos ZIPs RFB
# ---------------------------------------------------------------------------

def _open_csv_in_zip(zip_path: Path) -> tuple[zipfile.ZipFile, str]:
    """Abre o ZIP e devolve o nome do CSV interno (em geral 1 só)."""
    zf = zipfile.ZipFile(zip_path)
    candidatos = [
        n for n in zf.namelist()
        if not n.endswith("/")
        and ".pdf" not in n.lower()
    ]
    if not candidatos:
        raise RuntimeError(f"Nenhum arquivo dentro de {zip_path.name}")
    if len(candidatos) > 1:
        logger.warning("Múltiplos arquivos no ZIP %s, usando %s", zip_path.name, candidatos[0])
    return zf, candidatos[0]


def _read_simples(zip_path: Path) -> pd.DataFrame:
    """Lê Simples.zip inteiro em memória (~280 MB CSV → ~3-4 GB DataFrame string)."""
    zf, nome = _open_csv_in_zip(zip_path)
    logger.info("Lendo %s/%s ...", zip_path.name, nome)
    with zf.open(nome) as fh:
        df = pd.read_csv(
            fh,
            sep=";",
            header=None,
            names=SIMPLES_COLS,
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
            na_values=[""],
            low_memory=False,
        )
    zf.close()
    logger.info("Simples carregado: %d linhas", len(df))
    return df


def _read_municipios(zip_path: Path) -> pd.DataFrame:
    zf, nome = _open_csv_in_zip(zip_path)
    with zf.open(nome) as fh:
        df = pd.read_csv(
            fh,
            sep=";",
            header=None,
            names=MUNIC_COLS,
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
            quotechar='"',
        )
    zf.close()
    return df


def _iter_estabelecimentos_chunks(
    zip_path: Path, chunksize: int = 500_000,
) -> "pd.io.parsers.readers.TextFileReader":
    """Devolve iterador de chunks pandas para um Estabelecimentos*.zip."""
    zf, nome = _open_csv_in_zip(zip_path)
    fh = zf.open(nome)
    reader = pd.read_csv(
        fh,
        sep=";",
        header=None,
        names=ESTAB_COLS,
        usecols=list(ESTAB_USECOLS),
        dtype=str,
        encoding="latin-1",
        keep_default_na=False,
        na_values=[""],
        chunksize=chunksize,
        low_memory=True,
        on_bad_lines="warn",
    )
    # Anexa referências ao reader para fechar depois.
    reader._zf_handle = zf  # type: ignore[attr-defined]
    reader._fh_handle = fh  # type: ignore[attr-defined]
    return reader


# ---------------------------------------------------------------------------
# API pública: filter_mei
# ---------------------------------------------------------------------------

def filter_mei(dumps_dir: Path, periodo: str = DEFAULT_PERIODO) -> Path:
    """Aplica a estratégia em 4 passos e gera mei_ativos.parquet.

    Passo 1: Simples.zip → cnpj_basico de MEI vigente (opcao_mei='S' e
             data_exclusao_mei vazia/'0').
    Passo 2: Estabelecimentos0..9.zip → filtra matriz com cnpj_basico ∈ MEI.
    Passo 3: Enriquece com seção CNAE (de-para inline divisão→seção).
    Passo 4: Persiste em data/processed/mei_ativos.parquet com .meta.json.

    Args:
        dumps_dir: pasta com os ZIPs (data/raw/mei/<periodo>/).
        periodo:   'YYYY-MM' usado para metadados.

    Returns:
        Caminho do parquet final.
    """
    dumps_dir = Path(dumps_dir)

    # ----- Passo 1: Simples → conjunto de CNPJ_BASICO MEI vigente -----
    simples_zip = dumps_dir / "Simples.zip"
    if not simples_zip.exists():
        raise FileNotFoundError(f"Não encontrei {simples_zip}; rode download() antes.")
    simples = _read_simples(simples_zip)

    n_total_simples = len(simples)
    optantes_mei = simples[simples["opcao_mei"] == "S"]
    n_optantes_mei = len(optantes_mei)

    # MEI vigente = optou por MEI E não tem data de exclusão preenchida.
    # Convenção RFB: data_exclusao_mei == '0' (string) ou '00000000' ou NaN
    # quando o MEI segue ativo no Simples. Tratamos esses casos como vigente.
    def _exclusao_vazia(s: pd.Series) -> pd.Series:
        return s.isna() | (s == "") | (s == "0") | (s == "00000000")

    mei_vigente = optantes_mei[_exclusao_vazia(optantes_mei["data_exclusao_mei"])].copy()
    n_mei_vigente = len(mei_vigente)
    logger.info(
        "Simples: %d total | %d opcao_mei='S' | %d MEI vigente (sem data_exclusao_mei).",
        n_total_simples, n_optantes_mei, n_mei_vigente,
    )

    # Set para lookup O(1)
    cnpj_basicos_mei: set[str] = set(mei_vigente["cnpj_basico"].astype(str).tolist())
    # Mantemos as datas de opção/exclusão MEI para join no final
    mei_meta = mei_vigente[["cnpj_basico", "data_opcao_mei", "data_exclusao_mei"]].copy()
    mei_meta["cnpj_basico"] = mei_meta["cnpj_basico"].astype(str)
    del simples, optantes_mei, mei_vigente

    # ----- Passo 2: Estabelecimentos → matriz com cnpj_basico ∈ MEI -----
    estab_partes: list[pd.DataFrame] = []
    n_linhas_estab_total = 0
    n_linhas_matriz_mei = 0
    for i in range(10):
        z = dumps_dir / f"Estabelecimentos{i}.zip"
        if not z.exists():
            logger.warning("Pulando %s (não baixado).", z.name)
            continue
        logger.info("Processando %s em chunks...", z.name)
        reader = _iter_estabelecimentos_chunks(z, chunksize=500_000)
        for chunk in tqdm(reader, desc=z.name, unit="chunk", leave=False):
            n_linhas_estab_total += len(chunk)
            # Filtros: matriz E cnpj_basico ∈ MEI vigente
            mask_matriz = chunk["identificador_matriz_filial"] == "1"
            mask_mei = chunk["cnpj_basico"].isin(cnpj_basicos_mei)
            sel = chunk.loc[mask_matriz & mask_mei].copy()
            if not sel.empty:
                n_linhas_matriz_mei += len(sel)
                estab_partes.append(sel)
        # Fecha handles
        try:
            reader._fh_handle.close()  # type: ignore[attr-defined]
            reader._zf_handle.close()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    if not estab_partes:
        raise RuntimeError("Nenhum estabelecimento MEI matriz encontrado — verifique dumps.")

    estab_mei = pd.concat(estab_partes, ignore_index=True)
    del estab_partes
    logger.info(
        "Estabelecimentos: %d linhas totais | %d matrizes MEI vigente.",
        n_linhas_estab_total, n_linhas_matriz_mei,
    )

    # ----- Passo 3: Enriquecimento -----
    # 3a) seção CNAE
    estab_mei["cnae_principal_secao"] = estab_mei["cnae_fiscal_principal"].map(cnae_para_secao)

    # 3b) join com datas MEI do Simples
    estab_mei = estab_mei.merge(mei_meta, on="cnpj_basico", how="left")

    # 3c) flag mei_ativo: situação cadastral '02' (ativa) E presença em mei_vigente.
    # Como já filtramos por mei vigente, mei_ativo := situacao_cadastral == '02'.
    estab_mei["mei_ativo"] = estab_mei["situacao_cadastral"] == "02"

    # 3d) cnpj completo
    estab_mei["cnpj_completo"] = (
        estab_mei["cnpj_basico"].astype(str).str.zfill(8)
        + estab_mei["cnpj_ordem"].astype(str).str.zfill(4)
        + estab_mei["cnpj_dv"].astype(str).str.zfill(2)
    )

    # 3e) IBGE: deixar como NA por enquanto (ver nota no topo do módulo)
    estab_mei["municipio_codigo_ibge"] = pd.NA

    # 3f) renomes finais
    out = pd.DataFrame({
        "cnpj_basico":            estab_mei["cnpj_basico"].astype("string"),
        "cnpj_completo":          estab_mei["cnpj_completo"].astype("string"),
        "uf":                     estab_mei["uf"].astype("category"),
        "municipio_codigo_rfb":   estab_mei["municipio"].astype("string"),
        "municipio_codigo_ibge":  estab_mei["municipio_codigo_ibge"].astype("string"),
        "cnae_principal_classe":  estab_mei["cnae_fiscal_principal"].astype("string"),
        "cnae_principal_secao":   estab_mei["cnae_principal_secao"].astype("category"),
        "data_inicio_atividade":  estab_mei["data_inicio_atividade"].astype("string"),
        "data_opcao_mei":         estab_mei["data_opcao_mei"].astype("string"),
        "data_situacao_cadastral": estab_mei["data_situacao_cadastral"].astype("string"),
        "situacao_cadastral":     estab_mei["situacao_cadastral"].astype("category"),
        "mei_ativo":              estab_mei["mei_ativo"].astype(bool),
    })

    # ----- Passo 4: persistência -----
    final_path = paths.DATA_PROCESSED / "mei_ativos.parquet"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(final_path, index=False, compression="snappy")
    logger.info(
        "Parquet processed gerado: %s (%.1f MB)",
        final_path, final_path.stat().st_size / 1e6,
    )

    # Sanity numbers
    n_linhas = int(len(out))
    n_mei_ativo = int(out["mei_ativo"].sum())
    top_uf = (
        out.loc[out["mei_ativo"], "uf"].value_counts().head(5).to_dict()
    )
    top_uf = {str(k): int(v) for k, v in top_uf.items()}
    top_secao = (
        out.loc[out["mei_ativo"], "cnae_principal_secao"]
        .value_counts(dropna=False).head(5).to_dict()
    )
    top_secao = {(str(k) if pd.notna(k) else "NA"): int(v) for k, v in top_secao.items()}

    meta = {
        "periodo_snapshot": periodo,
        "n_linhas": n_linhas,
        "n_mei_ativo": n_mei_ativo,
        "n_simples_total": int(n_total_simples),
        "n_simples_opcao_mei_S": int(n_optantes_mei),
        "n_simples_mei_vigente": int(n_mei_vigente),
        "n_estabelecimentos_lidos": int(n_linhas_estab_total),
        "n_estabelecimentos_matriz_mei": int(n_linhas_matriz_mei),
        "top5_uf_mei_ativo": top_uf,
        "top5_secao_cnae_mei_ativo": top_secao,
        "colunas": list(out.columns),
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origem_dumps_dir": str(dumps_dir.relative_to(paths.ROOT)),
        "estrategia": "Simples(opcao_mei=S, sem data_exclusao) ∩ Estabelecimentos(matriz)",
        "obs_municipio_ibge": "código IBGE não resolvido nesta rodada (apenas RFB).",
    }
    final_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info("Sanity: n=%d  mei_ativo=%d  top_uf=%s  top_secao=%s",
                n_linhas, n_mei_ativo, top_uf, top_secao)

    return final_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periodo", default=DEFAULT_PERIODO,
                        help=f"snapshot YYYY-MM (default: {DEFAULT_PERIODO})")
    parser.add_argument("--force", action="store_true",
                        help="re-baixa mesmo que ZIPs já existam")
    parser.add_argument("--skip-download", action="store_true",
                        help="usa apenas ZIPs já presentes em data/raw/mei/<periodo>/")
    args = parser.parse_args()

    paths.ensure_dirs()
    if args.skip_download:
        dumps_dir = paths.RAW_MEI / args.periodo
        if not dumps_dir.exists():
            raise SystemExit(f"--skip-download mas {dumps_dir} não existe.")
    else:
        baixados = download(periodo=args.periodo, force=args.force)
        dumps_dir = baixados[0].parent

    final = filter_mei(dumps_dir, periodo=args.periodo)
    print(f"MEI processado: {final}")


if __name__ == "__main__":
    main()

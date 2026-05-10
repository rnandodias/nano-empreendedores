"""Camada de download HTTP compartilhada entre os módulos de ingestão.

Recursos:
- ``download_one``: download HTTP idempotente, com retomada via ``Range``,
  read-timeout por chunk, retry com backoff exponencial e .meta.json com
  hash sha256 + URL + datas. Funciona com Basic Auth (MEI) ou sem (PNADC).
- ``download_many``: pool de threads para baixar N arquivos em paralelo.
  Cada arquivo continua chamando ``download_one`` (independente, com sua
  própria retomada). O ganho vem de N conexões TCP simultâneas — necessário
  porque servidores brasileiros (RFB/IBGE) costumam serializar em ~2-3 MB/s
  por conexão, mesmo com banda do cliente sobrando.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults de robustez (override via DownloadConfig)
# ---------------------------------------------------------------------------

CONNECT_TIMEOUT_S = 30
READ_TIMEOUT_S = 60        # >60s sem bytes → dispara retomada
MAX_TENTATIVAS = 8
BACKOFF_BASE_S = 5
CHUNK_BYTES = 1 << 20      # 1 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while buf := f.read(chunk):
            h.update(buf)
    return h.hexdigest()


def make_session(auth: tuple[str, str] | None = None) -> requests.Session:
    s = requests.Session()
    if auth is not None:
        s.auth = auth
    s.headers.update({
        "Connection": "keep-alive",
        "Accept-Encoding": "identity",
    })
    return s


def write_meta(dest: Path, url: str, extra: dict | None = None) -> Path:
    """Grava ``<dest>.meta.json`` com hash, URL e timestamps."""
    meta = {
        "url": url,
        "arquivo": dest.name,
        "tamanho_bytes": dest.stat().st_size,
        "sha256": sha256(dest),
        "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if extra:
        meta.update(extra)
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta_path


# ---------------------------------------------------------------------------
# Item de download (entrada para download_many)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DownloadItem:
    url: str
    dest: Path
    auth: tuple[str, str] | None = None
    meta_extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Download de UM arquivo (idempotente, com Range e retry)
# ---------------------------------------------------------------------------

def download_one(
    item: DownloadItem,
    *,
    force: bool = False,
    position: int | None = None,
) -> Path:
    """Baixa um único arquivo, idempotente.

    - Se ``item.dest`` já existe e ``force=False`` → pula e retorna o caminho.
    - Senão, usa ``<dest>.part`` para escrita; em caso de erro de rede,
      retoma via ``Range: bytes=N-`` na próxima tentativa, sem perder bytes.
    - Read-timeout por chunk: se o servidor ficar > READ_TIMEOUT_S sem
      mandar bytes, dispara retry.
    - Após sucesso, grava ``<dest>.meta.json`` se não existir.
    - ``position`` é a linha do tqdm (para barras paralelas não pisarem).
    """
    if item.dest.exists() and not force:
        logger.info("Já existe, pulando: %s (%.1f MB)",
                    item.dest.name, item.dest.stat().st_size / 1e6)
        meta = item.dest.with_suffix(item.dest.suffix + ".meta.json")
        if not meta.exists():
            write_meta(item.dest, item.url, item.meta_extra)
        return item.dest

    item.dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = item.dest.with_suffix(item.dest.suffix + ".part")
    sess = make_session(item.auth)
    tentativa = 0

    while True:
        tentativa += 1
        ja_baixado = tmp.stat().st_size if tmp.exists() else 0
        headers: dict[str, str] = {}
        if ja_baixado > 0:
            headers["Range"] = f"bytes={ja_baixado}-"
            logger.info("Retomada %s a partir de %.1f MB (tentativa %d/%d)",
                        item.dest.name, ja_baixado / 1e6, tentativa, MAX_TENTATIVAS)
        else:
            logger.info("Baixando %s (tentativa %d/%d)", item.dest.name,
                        tentativa, MAX_TENTATIVAS)

        try:
            with sess.get(
                item.url, headers=headers, stream=True,
                timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S),
            ) as r:
                if r.status_code == 200 and ja_baixado > 0:
                    logger.warning("Servidor ignorou Range; reiniciando %s do zero", item.dest.name)
                    tmp.unlink(missing_ok=True)
                    ja_baixado = 0
                r.raise_for_status()

                total_resto = int(r.headers.get("Content-Length", 0))
                total_final = ja_baixado + total_resto
                modo = "ab" if ja_baixado > 0 else "wb"
                with tmp.open(modo) as f, tqdm(
                    total=total_final, initial=ja_baixado,
                    unit="B", unit_scale=True,
                    desc=item.dest.name, leave=False,
                    position=position, mininterval=2.0,
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=CHUNK_BYTES):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            tmp.replace(item.dest)
            logger.info("Concluído: %s (%.1f MB)",
                        item.dest.name, item.dest.stat().st_size / 1e6)
            write_meta(item.dest, item.url, item.meta_extra)
            return item.dest

        except (requests.exceptions.RequestException, OSError) as exc:
            if tentativa >= MAX_TENTATIVAS:
                logger.error("Falha definitiva em %s após %d tentativas: %s",
                             item.dest.name, tentativa, exc)
                raise
            espera = BACKOFF_BASE_S * (2 ** (tentativa - 1))
            logger.warning("Erro em %s (tentativa %d): %s — retomando em %ds",
                           item.dest.name, tentativa, exc, espera)
            time.sleep(espera)


# ---------------------------------------------------------------------------
# Download paralelo
# ---------------------------------------------------------------------------

def download_many(
    items: list[DownloadItem],
    *,
    max_workers: int = 4,
    force: bool = False,
) -> list[Path]:
    """Baixa N arquivos em paralelo via ThreadPoolExecutor.

    Cada worker chama ``download_one`` em um item independente. Falhas são
    re-erguidas após esgotar todas as N tentativas internas. Atomicidade:
    cada arquivo só vira ``dest`` final quando o ``.part`` está completo.

    Args:
        items: lista de DownloadItem.
        max_workers: número de downloads simultâneos. Para servidores
            brasileiros (RFB/IBGE) o sweet spot é 4-6 — mais que isso o
            server costuma rate-limitar ou degradar a velocidade individual.
        force: força re-download mesmo se ``dest`` existe.

    Returns:
        Lista de Paths concluídos, na ordem original.
    """
    resultados: dict[int, Path] = {}
    erros: list[tuple[DownloadItem, BaseException]] = []

    logger.info("Iniciando download paralelo: %d arquivos, %d workers",
                len(items), max_workers)
    inicio = time.time()

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dl") as pool:
        futuros = {
            pool.submit(download_one, item, force=force, position=i % max_workers): (i, item)
            for i, item in enumerate(items)
        }
        for fut in as_completed(futuros):
            idx, item = futuros[fut]
            try:
                resultados[idx] = fut.result()
            except BaseException as exc:  # noqa: BLE001
                logger.error("Item falhou definitivamente: %s -> %s", item.url, exc)
                erros.append((item, exc))

    decorrido = time.time() - inicio
    logger.info("Download paralelo concluído em %.1f min (%d sucessos, %d falhas)",
                decorrido / 60, len(resultados), len(erros))

    if erros:
        msg = "; ".join(f"{i.dest.name}: {e}" for i, e in erros[:5])
        raise RuntimeError(f"Falhas em {len(erros)} downloads: {msg}")

    return [resultados[i] for i in sorted(resultados)]

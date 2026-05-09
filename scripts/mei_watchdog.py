"""Watchdog + orquestrador para a ingestão MEI.

Faz três coisas em paralelo:
1. Mantém UM processo `python -m src.ingest.mei --periodo <X>` rodando.
   Se ele morrer (crash) ou for morto (stall), relança automaticamente.
   O `_http_download` patcheado retoma cada arquivo via Range, sem perder bytes.
2. Detecta stall: se algum `.part` ficar parado > STALL_S sem crescer,
   mata o filho — o loop principal relança e o Range continua de onde parou.
3. Escreve `data/raw/mei/STATUS.txt` a cada INTERVALO_S com snapshot legível
   (arquivos baixados, tamanhos, mtime, último log). O usuário pode abrir/
   `Get-Content -Tail 30 -Wait` esse arquivo a qualquer momento.

Sai com código 0 quando `data/processed/mei_ativos.parquet` aparece.
Sai com código 2 em hard timeout.

Uso:
    python scripts/mei_watchdog.py [--periodo 2026-04] [--max-restarts 12]
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "mei"
PROC_DIR = ROOT / "data" / "processed"
STATUS = RAW_DIR / "STATUS.txt"
PARQUET_FINAL = PROC_DIR / "mei_ativos.parquet"
LOG_GLOB = "run-*.log"

INTERVALO_S = 30
STALL_S = 180          # 3 min sem .part crescer = stall
TIMEOUT_TOTAL_S = 5 * 3600  # 5h hard timeout
START_TS = time.time()


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _snapshot(child_pid: int | None, restarts: int, periodo: str) -> str:
    linhas: list[str] = []
    elapsed = time.time() - START_TS
    linhas.append(f"=== MEI WATCHDOG @ {_agora()}  (decorrido: {elapsed/60:.1f} min) ===")
    linhas.append(f"Snapshot alvo: {periodo}")
    linhas.append(
        f"Subprocesso filho: pid={child_pid if child_pid else '(nenhum)'}  "
        f"restarts={restarts}"
    )

    if PARQUET_FINAL.exists():
        sz = PARQUET_FINAL.stat().st_size / 1e6
        linhas.append("")
        linhas.append(f">>> SUCESSO: {PARQUET_FINAL.name} ({sz:.1f} MB) <<<")

    snap_dir = RAW_DIR / periodo
    if snap_dir.exists():
        linhas.append(f"\nArquivos em {snap_dir.relative_to(ROOT)}:")
        total_bytes = 0
        for arq in sorted(snap_dir.iterdir()):
            sz_b = arq.stat().st_size
            total_bytes += sz_b
            mtime = datetime.fromtimestamp(arq.stat().st_mtime).strftime("%H:%M:%S")
            tag = ""
            if arq.suffix == ".part":
                age = time.time() - arq.stat().st_mtime
                tag = f"  [parado {age:.0f}s]" if age > 60 else "  [crescendo]"
            linhas.append(
                f"  {arq.name:42s} {sz_b/1e6:9.2f} MB  mtime={mtime}{tag}"
            )
        linhas.append(f"  {'TOTAL':42s} {total_bytes/1e9:9.2f} GB")

    logs = sorted(RAW_DIR.glob(LOG_GLOB))
    if logs:
        log = logs[-1]
        try:
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-6:]
            linhas.append(f"\nÚltimas linhas de {log.name}:")
            linhas.extend(f"  {l[:140]}" for l in tail)
        except Exception as exc:
            linhas.append(f"\n(erro lendo log: {exc})")

    return "\n".join(linhas) + "\n"


def _abrir_log() -> Path:
    return RAW_DIR / f"run-{datetime.now().strftime('%Y-%m-%d')}.log"


def _spawn(periodo: str) -> tuple[subprocess.Popen, Path]:
    log_path = _abrir_log()
    log_fh = log_path.open("ab")
    log_fh.write(f"\n\n=== {_agora()} :: spawn `python -m src.ingest.mei --periodo {periodo}` ===\n".encode())
    log_fh.flush()
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "src.ingest.mei", "--periodo", periodo],
        cwd=str(ROOT),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    return proc, log_path


def _matar(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=10)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception as exc:
        print(f"[watchdog] erro matando pid {proc.pid}: {exc}", file=sys.stderr)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periodo", default="2026-04")
    parser.add_argument("--max-restarts", type=int, default=20)
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    proc: subprocess.Popen | None = None
    restarts = 0
    last_part_size: dict[str, int] = {}
    last_part_change: dict[str, float] = {}

    print(f"[watchdog] iniciando para snapshot {args.periodo}", file=sys.stderr)
    print(f"[watchdog] STATUS em {STATUS}", file=sys.stderr)

    try:
        while True:
            # Hard timeout
            if time.time() - START_TS > TIMEOUT_TOTAL_S:
                print("[watchdog] HARD TIMEOUT 5h", file=sys.stderr)
                if proc:
                    _matar(proc)
                STATUS.write_text(
                    _snapshot(proc.pid if proc else None, restarts, args.periodo)
                    + "\n!!! HARD TIMEOUT 5h !!!\n",
                    encoding="utf-8",
                )
                return 2

            # Sucesso?
            if PARQUET_FINAL.exists():
                print("[watchdog] parquet final detectado", file=sys.stderr)
                if proc and proc.poll() is None:
                    proc.wait(timeout=5)
                STATUS.write_text(
                    _snapshot(proc.pid if proc else None, restarts, args.periodo),
                    encoding="utf-8",
                )
                return 0

            # Garante 1 filho rodando
            if proc is None or proc.poll() is not None:
                if proc is not None:
                    rc = proc.returncode
                    print(f"[watchdog] filho saiu com código {rc}", file=sys.stderr)
                if restarts >= args.max_restarts:
                    print(f"[watchdog] excedeu --max-restarts={args.max_restarts}", file=sys.stderr)
                    return 3
                if restarts > 0:
                    espera = min(60, 5 * (2 ** min(restarts, 5)))
                    print(f"[watchdog] aguardando {espera}s antes de relançar...", file=sys.stderr)
                    time.sleep(espera)
                proc, _ = _spawn(args.periodo)
                restarts += 1
                # Reset de detecção de stall ao relançar
                last_part_change.clear()
                last_part_size.clear()

            # Atualiza STATUS.txt
            try:
                STATUS.write_text(
                    _snapshot(proc.pid if proc else None, restarts, args.periodo),
                    encoding="utf-8",
                )
            except Exception as exc:
                print(f"[watchdog] erro escrevendo STATUS: {exc}", file=sys.stderr)

            # Stall detection
            snap_dir = RAW_DIR / args.periodo
            if snap_dir.exists():
                for arq in snap_dir.glob("*.part"):
                    sz = arq.stat().st_size
                    key = arq.name
                    agora = time.time()
                    if last_part_size.get(key) != sz:
                        last_part_size[key] = sz
                        last_part_change[key] = agora
                    else:
                        parado = agora - last_part_change.get(key, agora)
                        if parado > STALL_S and proc and proc.poll() is None:
                            print(
                                f"[watchdog] STALL {key} parado {parado:.0f}s -> matando filho",
                                file=sys.stderr,
                            )
                            _matar(proc)
                            # próximo loop relança via Range
                            break

            time.sleep(INTERVALO_S)

    except KeyboardInterrupt:
        print("[watchdog] interrompido pelo usuário", file=sys.stderr)
        if proc:
            _matar(proc)
        return 130


if __name__ == "__main__":
    sys.exit(main())

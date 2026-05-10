"""Watchdog + orquestrador para a ingestão MEI (multi-período).

Faz três coisas em paralelo:
1. Mantém UM processo `python -m src.ingest.mei --periodos <lista>` rodando.
   Se ele morrer (crash) ou for morto (stall), relança automaticamente.
   O `_http.download_one` retoma cada arquivo via Range, sem perder bytes.
2. Detecta stall: se algum `.part` em qualquer período ficar parado > STALL_S
   sem crescer, mata o filho. O loop relança e o Range continua de onde parou.
3. Escreve `data/raw/mei/STATUS.txt` a cada INTERVALO_S com snapshot legível
   de TODOS os períodos em andamento. Acompanhar com:
       Get-Content -Path data\raw\mei\STATUS.txt -Wait

Sai com código 0 quando os parquets finais de TODOS os períodos existirem.
Sai com código 2 em hard timeout.

Uso:
    python scripts/mei_watchdog.py --periodos 2025-03,2025-06,2025-09,2025-12
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
LOG_GLOB = "run-*.log"


def _parquet_final(periodo: str) -> Path:
    return PROC_DIR / f"mei_ativos_{periodo}.parquet"


def _todos_parquets_existem(periodos: list[str]) -> bool:
    return all(_parquet_final(p).exists() for p in periodos)

INTERVALO_S = 30
STALL_S = 180          # 3 min sem .part crescer = stall
TIMEOUT_TOTAL_S = 5 * 3600  # 5h hard timeout
START_TS = time.time()


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _snapshot(child_pid: int | None, restarts: int, periodos: list[str]) -> str:
    linhas: list[str] = []
    elapsed = time.time() - START_TS
    linhas.append(f"=== MEI WATCHDOG @ {_agora()}  (decorrido: {elapsed/60:.1f} min) ===")
    linhas.append(f"Snapshots alvo ({len(periodos)}): {', '.join(periodos)}")
    linhas.append(
        f"Subprocesso filho: pid={child_pid if child_pid else '(nenhum)'}  "
        f"restarts={restarts}"
    )

    # Status agregado dos parquets finais
    prontos = [p for p in periodos if _parquet_final(p).exists()]
    pendentes = [p for p in periodos if not _parquet_final(p).exists()]
    linhas.append(f"\nParquets finais: {len(prontos)}/{len(periodos)} prontos")
    if prontos:
        for p in prontos:
            sz = _parquet_final(p).stat().st_size / 1e6
            linhas.append(f"  ✓ {_parquet_final(p).name} ({sz:.1f} MB)")
    if not pendentes:
        linhas.append("\n>>> SUCESSO TOTAL: todos os períodos processados <<<")

    # Detalhe por snapshot pendente
    total_geral = 0
    for periodo in periodos:
        snap_dir = RAW_DIR / periodo
        if not snap_dir.exists():
            linhas.append(f"\n[{periodo}] (pasta ainda não criada)")
            continue
        sub_total = 0
        n_part = 0
        n_zip = 0
        for arq in snap_dir.iterdir():
            sub_total += arq.stat().st_size
            if arq.suffix == ".part":
                n_part += 1
            elif arq.suffix == ".zip":
                n_zip += 1
        total_geral += sub_total
        linhas.append(f"\n[{periodo}] {n_zip} ZIPs · {n_part} .part · {sub_total/1e9:.2f} GB")
        # Mostra apenas .part (mais informativo durante download)
        for arq in sorted(snap_dir.glob("*.part")):
            sz_b = arq.stat().st_size
            mtime = datetime.fromtimestamp(arq.stat().st_mtime).strftime("%H:%M:%S")
            age = time.time() - arq.stat().st_mtime
            tag = f"[parado {age:.0f}s]" if age > 60 else "[crescendo]"
            linhas.append(f"    {arq.name:30s} {sz_b/1e6:9.2f} MB  mtime={mtime} {tag}")

    linhas.append(f"\nTotal em data/raw/mei/: {total_geral/1e9:.2f} GB")

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


def _spawn(periodos: list[str], max_workers: int) -> tuple[subprocess.Popen, Path]:
    log_path = _abrir_log()
    log_fh = log_path.open("ab")
    csv_periodos = ",".join(periodos)
    cmd = [
        sys.executable, "-u", "-m", "src.ingest.mei",
        "--periodos", csv_periodos,
        "--max-workers", str(max_workers),
    ]
    log_fh.write(f"\n\n=== {_agora()} :: spawn `{' '.join(cmd)}` ===\n".encode())
    log_fh.flush()
    proc = subprocess.Popen(
        cmd, cwd=str(ROOT), stdout=log_fh, stderr=subprocess.STDOUT,
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
    parser.add_argument("--periodos", required=True,
                        help="lista de snapshots, ex.: 2025-03,2025-06,2025-09,2025-12")
    parser.add_argument("--max-workers", type=int, default=4,
                        help="downloads simultâneos do filho mei.py")
    parser.add_argument("--max-restarts", type=int, default=20)
    args = parser.parse_args()

    periodos = [p.strip() for p in args.periodos.split(",") if p.strip()]
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    proc: subprocess.Popen | None = None
    restarts = 0
    last_part_size: dict[str, int] = {}
    last_part_change: dict[str, float] = {}

    print(f"[watchdog] iniciando para snapshots {periodos}", file=sys.stderr)
    print(f"[watchdog] STATUS em {STATUS}", file=sys.stderr)

    try:
        while True:
            # Hard timeout
            if time.time() - START_TS > TIMEOUT_TOTAL_S:
                print("[watchdog] HARD TIMEOUT 5h", file=sys.stderr)
                if proc:
                    _matar(proc)
                STATUS.write_text(
                    _snapshot(proc.pid if proc else None, restarts, periodos)
                    + "\n!!! HARD TIMEOUT 5h !!!\n",
                    encoding="utf-8",
                )
                return 2

            # Sucesso = todos os parquets prontos
            if _todos_parquets_existem(periodos):
                print("[watchdog] todos os parquets finais detectados", file=sys.stderr)
                if proc and proc.poll() is None:
                    proc.wait(timeout=10)
                STATUS.write_text(
                    _snapshot(proc.pid if proc else None, restarts, periodos),
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
                proc, _ = _spawn(periodos, args.max_workers)
                restarts += 1
                last_part_change.clear()
                last_part_size.clear()

            try:
                STATUS.write_text(
                    _snapshot(proc.pid if proc else None, restarts, periodos),
                    encoding="utf-8",
                )
            except Exception as exc:
                print(f"[watchdog] erro escrevendo STATUS: {exc}", file=sys.stderr)

            # Stall detection — varre .part de TODOS os períodos
            mato = False
            for periodo in periodos:
                snap_dir = RAW_DIR / periodo
                if not snap_dir.exists():
                    continue
                for arq in snap_dir.glob("*.part"):
                    sz = arq.stat().st_size
                    key = f"{periodo}/{arq.name}"
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
                            mato = True
                            break
                if mato:
                    break

            time.sleep(INTERVALO_S)

    except KeyboardInterrupt:
        print("[watchdog] interrompido pelo usuário", file=sys.stderr)
        if proc:
            _matar(proc)
        return 130


if __name__ == "__main__":
    sys.exit(main())

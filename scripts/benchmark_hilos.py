#!/usr/bin/env python
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Benchmark escalonado de hilos y procesos de `webtechstats scan`.

Un nivel es `PxW` (P procesos × W hilos cada uno) o solo `W` (1 proceso). Para cada nivel importa los N primeros sitios del CSV en un lote temporal propio (así todos los niveles
escanean exactamente los mismos dominios), lanza `webtechstats scan --workers NIVEL` y muestrea el proceso
(CPU, memoria, hilos, descriptores, conexiones) y el progreso en MongoDB. Al final compara los niveles:
ritmo, tiempo hasta el 90 %, fallos por motivo y *fallos inducidos* (sitios que fallan en el nivel y no
fallaron en el de referencia: saturación, no dominios muertos). Borra los lotes temporales al terminar.

Uso: uv run python scripts/benchmark_hilos.py [--levels 16 32 4x8 8x8 16x8] [--sites 1000] [--keep]
Salida: tabla por stdout (redirigir a logs/) y CSV en logs/benchmark_hilos_<fecha>.csv
"""

import argparse
import csv
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import psutil

from webtechstats.db import close_db, init_db
from webtechstats.importer import import_sites
from webtechstats.models import Site

ROOT = Path(__file__).resolve().parents[1]
BASE_BATCH = 9000


def done_filter(batch: int) -> dict:
    return {"batch": batch, "$or": [{"finished": True}, {"discarded": True}]}


def sample(root: psutil.Process, known: dict, last_net):
    """Suma el proceso padre y todos sus hijos. `cpu_proc` 100 = un núcleo completo."""
    net = psutil.net_io_counters()
    procs = [root] + root.children(recursive=True)
    row = {"cpu_proc": 0.0, "rss_mb": 0.0, "threads": 0, "fds": 0, "conns": 0}
    for p in procs:
        p = known.setdefault(p.pid, p)  # se reutiliza el objeto para que cpu_percent mida entre muestras
        try:
            row["cpu_proc"] += p.cpu_percent(None)
            row["rss_mb"] += p.memory_info().rss / 2**20
            row["threads"] += p.num_threads()
            row["fds"] += p.num_fds()
            row["conns"] += len(p.net_connections())
        except psutil.Error:
            continue
    row["cpu_sys"] = psutil.cpu_percent(None)
    row["net_kbs"] = (net.bytes_recv + net.bytes_sent - last_net) / 1024
    row["procs"] = len(procs)
    return row, net.bytes_recv + net.bytes_sent


def parse_level(text: str) -> tuple[int, int]:
    """`16` -> (1, 16); `8x4` -> (8, 4)."""
    procs, _, workers = text.lower().rpartition("x")
    return (int(procs) if procs else 1), int(workers)


def run_level(index: int, processes: int, workers: int, args) -> dict:
    batch = BASE_BATCH + index + 1
    collection = Site._get_collection()
    if collection.count_documents({"batch": batch}):
        sys.exit(f"El lote temporal {batch} ya existe: bórralo antes de repetir el benchmark.")
    import_sites(args.csv, limit=args.sites, batch=batch)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    scan_log = ROOT / "logs" / f"benchmark_scan_{processes}x{workers}_batch-{batch}_{stamp}.log"
    exe = Path(sys.executable).parent / "webtechstats"
    with open(scan_log, "w") as out:
        proc = subprocess.Popen(
            [str(exe), "scan", "--limit", str(args.sites), "--batch", str(batch), "--workers", str(workers),
             "--processes", str(processes)],
            stdout=out, stderr=out, cwd=ROOT,
        )
    ps = psutil.Process(proc.pid)
    known = {ps.pid: ps}
    ps.cpu_percent(None)
    psutil.cpu_percent(None)
    last_net = psutil.net_io_counters()
    last_net = last_net.bytes_recv + last_net.bytes_sent

    started = time.monotonic()
    samples, t90, stopped = [], None, False
    while proc.poll() is None:
        time.sleep(args.interval)
        elapsed = time.monotonic() - started
        try:
            row, last_net = sample(ps, known, last_net)
        except psutil.Error:
            break
        done = collection.count_documents(done_filter(batch))
        row.update(t=round(elapsed), done=done)
        samples.append(row)
        if t90 is None and done >= 0.9 * args.sites:
            t90 = elapsed
        print(f"  [{processes}x{workers}] t={elapsed:5.0f}s hechos={done:>4} cpu={row['cpu_proc']:5.0f}% "
              f"(sistema {row['cpu_sys']:3.0f}%) rss={row['rss_mb']:5.0f}MB hilos={row['threads']:>3} "
              f"fds={row['fds']:>4} conns={row['conns']:>3} "
              f"red={row['net_kbs']:7.0f}KB/s", flush=True)
        if elapsed > args.max_seconds and not stopped:
            print("  límite de tiempo: parada ordenada del nivel", flush=True)
            proc.send_signal(signal.SIGTERM)
            stopped = True
    total = time.monotonic() - started

    ok = collection.count_documents({"batch": batch, "finished": True})
    failed_docs = list(collection.find({"batch": batch, "discarded": True}, {"url": 1, "discard_reason": 1}))
    done = ok + len(failed_docs)
    return {
        "level": f"{processes}x{workers}", "processes": processes, "workers": workers,
        "concurrency": processes * workers, "batch": batch, "done": done, "ok": ok, "failed": len(failed_docs),
        "fail_pct": round(100 * len(failed_docs) / max(done, 1), 1),
        "seconds": round(total), "per_min": round(60 * done / total) if total else 0,
        "t90_s": round(t90) if t90 else None,
        "per_min_90": round(60 * 0.9 * args.sites / t90) if t90 else None,
        "cpu_avg": round(sum(s["cpu_proc"] for s in samples) / max(len(samples), 1)),
        "cpu_sys_max": round(max((s["cpu_sys"] for s in samples), default=0)),
        "cpu_max": round(max((s["cpu_proc"] for s in samples), default=0)),
        "rss_max_mb": round(max((s["rss_mb"] for s in samples), default=0)),
        "threads_max": max((s["threads"] for s in samples), default=0),
        "fds_max": max((s["fds"] for s in samples), default=0),
        "conns_max": max((s["conns"] for s in samples), default=0),
        "net_max_kbs": round(max((s["net_kbs"] for s in samples), default=0)),
        "reasons": dict(Counter(d.get("discard_reason") for d in failed_docs)),
        "failed_urls": {d["url"] for d in failed_docs},
        "completed": not stopped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--levels", nargs="+", default=["16", "32", "4x8", "8x8", "16x8"],
                        help="niveles: `W` (1 proceso × W hilos) o `PxW`")
    parser.add_argument("--sites", type=int, default=1000, help="primeros N sitios del CSV que usa cada nivel")
    parser.add_argument("--csv", default=str(ROOT / "top-1m.csv"))
    parser.add_argument("--interval", type=float, default=5.0, help="segundos entre muestras")
    parser.add_argument("--max-seconds", type=int, default=1800, help="tope por nivel (parada ordenada)")
    parser.add_argument("--keep", action="store_true", help="no borrar los lotes temporales")
    args = parser.parse_args()

    print(f"CPUs disponibles para el benchmark (afinidad): {sorted(os.sched_getaffinity(0))}", flush=True)
    init_db()
    Site.ensure_schema()
    results, created = [], []
    try:
        for i, level in enumerate(args.levels):
            processes, workers = parse_level(level)
            print(f"\n=== Nivel {i + 1}/{len(args.levels)}: {processes} proceso(s) × {workers} hilos "
                  f"({processes * workers} simultáneas), primeros {args.sites} sitios ===", flush=True)
            created.append(BASE_BATCH + i + 1)
            results.append(run_level(i, processes, workers, args))
            r = results[-1]
            print(f"  → {r['done']} hechos en {r['seconds']}s ({r['per_min']}/min), fallos {r['fail_pct']}% {r['reasons']}", flush=True)
    finally:
        if not args.keep:
            for batch in created:
                Site.objects(batch=batch).delete()
        close_db()

    base = results[0]["failed_urls"]
    for r in results:
        r["induced_failures"] = len(r["failed_urls"] - base)
        r["recovered"] = len(base - r["failed_urls"])

    cols = ["level", "concurrency", "done", "ok", "failed", "fail_pct", "induced_failures", "recovered", "seconds", "per_min",
            "t90_s", "per_min_90", "cpu_avg", "cpu_max", "cpu_sys_max", "rss_max_mb", "threads_max", "fds_max", "conns_max",
            "net_max_kbs", "completed"]
    out_csv = ROOT / "logs" / f"benchmark_hilos_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    with open(out_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(cols + ["reasons"])
        for r in results:
            writer.writerow([r[c] for c in cols] + [r["reasons"]])

    print("\n=== RESUMEN (referencia de fallos: primer nivel) ===")
    print(" ".join(f"{c:>9}" for c in cols))
    for r in results:
        print(" ".join(f"{str(r[c]):>9}" for c in cols))
    for r in results:
        print(f"  {r['level']:>6} — motivos de fallo: {r['reasons']}")
    print(f"\nCSV: {out_csv}")


if __name__ == "__main__":
    main()

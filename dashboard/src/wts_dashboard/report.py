# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Exporta un lote como informe estático: JSON con los agregados, sin MongoDB en tiempo de consulta.

Por cada corte del ranking (Top 100, 1k ... 1M) y para "todos" se escribe `<id>/top-<N>.json`
(`top-all.json`) con el resumen y el ranking completo de cada tema; `index.json` lista los informes.
Solo hay agregados: ningún dominio sale de la base de datos.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from webtechstats.config import MongoConfig
from webtechstats.db import close_db, init_db
from webtechstats.stats import batch_info
from webtechstats.topics import TOPICS

from .service import DashboardService

# Mismos cortes que el selector «Nº de sitios» del frontend.
TOP_STEPS = [100, 1_000, 10_000, 100_000, *[n * 100_000 for n in range(2, 10)], 1_000_000]
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ALL = 10**9  # sin tope práctico: el ranking completo de cada tema


def connect_db() -> None:
    init_db(MongoConfig.load())


def disconnect_db() -> None:
    close_db()


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    tmp.replace(path)  # nunca queda un JSON a medias


def _cut(service: DashboardService, report_id: str, batch: int, max_position: int | None, tld: str | None = None) -> dict:
    overview = service.overview(batch, max_position, tld)
    topics = []
    for t in overview["topics"]:
        ranking = service.topic_ranking(t["key"], batch=batch, limit=_ALL, max_position=max_position, tld=tld)
        topics.append(
            {
                "key": t["key"],
                "label": TOPICS[t["key"]],
                "distinct": ranking["total_items"],
                "categories": ranking["categories"],
                "items": ranking["items"],
            }
        )
    return {
        "report": report_id,
        "max_position": max_position,
        "tld": tld,
        "summary": {
            key: overview[key]
            for key in ("total", "finished", "pending", "failed", "with_tech", "distinct_tech")
        },
        "topics": topics,
    }


def export_report(
    service: DashboardService,
    report_id: str,
    label: str,
    batch: int,
    out_dir: Path,
    year: int | None = None,
    steps: list[int] | None = None,
    tld: str | None = None,
    min_sites: int | None = None,
) -> dict:
    """Escribe el informe del lote y actualiza `index.json`. Devuelve la entrada del índice."""
    if not _ID.match(report_id or ""):
        raise ValueError(f"identificador de informe no válido: {report_id!r}")
    info = next((b for b in batch_info() if b["batch"] == batch), None)
    if info is None:
        raise ValueError(f"el lote {batch} no existe o está vacío")
    out_dir = Path(out_dir)
    # Con un tld (p. ej. es) los primeros cortes casi no tienen sitios: se omiten los de menos de `min_sites`.
    min_sites = (30 if tld else 0) if min_sites is None else min_sites
    tops = []
    for n in (TOP_STEPS if steps is None else steps):
        if n > info["total"]:
            continue
        cut = _cut(service, report_id, batch, n, tld)
        if cut["summary"]["finished"] >= max(min_sites, 1):
            _write(out_dir / report_id / f"top-{n}.json", cut)
            tops.append(n)
    everything = _cut(service, report_id, batch, None, tld)
    _write(out_dir / report_id / "top-all.json", everything)
    totals = everything["summary"]

    entry = {
        "id": report_id,
        "label": label,
        "year": year if year is not None else date.today().year,
        "batch": batch,
        "generated": datetime.now().replace(microsecond=0).isoformat(),
        "last_activity": info["last_activity"],
        "scope": tld or "all",
        "tld": tld,
        "total": totals["total"],
        "finished": totals["finished"],
        "failed": totals["failed"],
        "tops": tops,
    }
    index_path = out_dir / "index.json"
    reports = json.loads(index_path.read_text())["reports"] if index_path.is_file() else []
    reports = [r for r in reports if r["id"] != report_id] + [entry]
    reports.sort(key=lambda r: (r["year"], r["id"]))
    _write(index_path, {"reports": reports})
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta un lote como informe estático (JSON).")
    parser.add_argument("--batch", type=int, required=True, help="lote a exportar")
    parser.add_argument("--id", required=True, help="identificador del informe (nombre de carpeta), p. ej. 2026")
    parser.add_argument("--label", help="etiqueta visible (por defecto, el identificador)")
    parser.add_argument("--year", type=int, help="año del informe (por defecto, el actual)")
    parser.add_argument("--tld", help="solo dominios .TLD (p. ej. es); genera un informe de ámbito acotado")
    parser.add_argument("--out", default="reports", help="carpeta de salida (por defecto ./reports)")
    args = parser.parse_args(argv)
    connect_db()
    try:
        entry = export_report(
            DashboardService(cache_ttl=3600), args.id, args.label or args.id, args.batch, Path(args.out), args.year, tld=args.tld
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        disconnect_db()
    print(f"Informe {entry['id']}: {entry['finished']} de {entry['total']} sitios, cortes {entry['tops']} + todos → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

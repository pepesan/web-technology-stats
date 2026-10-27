# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Agregados sobre la colección `Site`."""

import re

from .models import Site


def _tld_regex(tld: str) -> str:
    """Dominios que terminan en `.<tld>` (el tld se escapa: se compara literalmente)."""
    return rf"\.{re.escape(tld.lstrip('.'))}$"


def summary(
    batch: int | None = None, max_position: int | None = None, tld: str | None = None, source: str | None = None
) -> dict:
    """Totales de todos los lotes, o solo del lote indicado.

    `max_position` limita a los sitios del top N del ranking (`position <= N`), `tld` a los dominios `.tld` y
    `source` a los dominios que proceden de ese listado (ver `Site.sources`).
    """
    sites = Site.objects if batch is None else Site.objects(batch=batch)
    if max_position is not None:
        sites = sites(position__lte=max_position)
    if tld:
        sites = sites(url=re.compile(_tld_regex(tld)))
    if source:
        sites = sites(sources=source)
    total = sites.count()
    finished = sites(finished=True).count()
    failed = sites(finished=False, retries__gt=0).count()  # intentados sin éxito ("sin respuesta")
    pending = total - finished - failed  # nunca intentados
    with_tech = sites(finished=True, tech__ne=[]).count()
    return {
        "total": total,
        "finished": finished,
        "pending": pending,
        "failed": failed,
        "finished_with_tech": with_tech,
    }


def batches() -> list[int]:
    """Identificadores de lote presentes en la colección, ordenados."""
    return sorted(int(b) for b in Site.objects.distinct("batch"))


def batch_info() -> list[dict]:
    """Resumen por lote (una ejecución): sitios, analizados, sin respuesta y última actividad."""
    pipeline = [
        {
            "$group": {
                "_id": "$batch",
                "total": {"$sum": 1},
                "finished": {"$sum": {"$cond": ["$finished", 1, 0]}},
                "failed": {
                    "$sum": {"$cond": [{"$and": [{"$ne": ["$finished", True]}, {"$gt": ["$retries", 0]}]}, 1, 0]}
                },
                "last_activity": {"$max": "$last_search_datetime"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = Site._get_collection().aggregate(pipeline)
    return [
        {
            "batch": int(r["_id"]),
            "total": r["total"],
            "finished": r["finished"],
            "failed": r["failed"],
            "last_activity": r["last_activity"].isoformat() if r.get("last_activity") else None,
        }
        for r in rows
    ]


def top_technologies(
    top: int | None = 20,
    batch: int | None = None,
    max_position: int | None = None,
    tld: str | None = None,
    source: str | None = None,
) -> list[dict]:
    """Ranking de tecnologías; `top=None` devuelve todas. `max_position` limita al top N del ranking, `tld` a `.tld`
    y `source` a los dominios de ese listado."""
    match = {"finished": True} if batch is None else {"finished": True, "batch": batch}
    if max_position is not None:
        match["position"] = {"$lte": max_position}
    if tld:
        match["url"] = {"$regex": _tld_regex(tld)}
    if source:
        match["sources"] = source
    pipeline = [
        {"$match": match},
        {"$unwind": "$tech"},
        {"$group": {"_id": "$tech", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]
    if top is not None:
        pipeline.append({"$limit": top})
    collection = Site._get_collection()
    return [{"tech": doc["_id"], "count": doc["count"]} for doc in collection.aggregate(pipeline)]


def source_overlap(batch: int | None = None) -> list[dict]:
    """Cuántos sitios hay por cada combinación de listados de origen (`[]` = sin etiquetar).

    El mismo conjunto cuenta junto aunque las fuentes se guardaran en otro orden. Más frecuentes primero.
    """
    pipeline = [{"$match": {} if batch is None else {"batch": batch}}, {"$group": {"_id": "$sources", "count": {"$sum": 1}}}]
    merged: dict[tuple, int] = {}
    for doc in Site._get_collection().aggregate(pipeline):
        key = tuple(sorted(doc["_id"] or []))
        merged[key] = merged.get(key, 0) + doc["count"]
    ordered = sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    return [{"sources": list(key), "count": count} for key, count in ordered]

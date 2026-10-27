# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Importación de listados de dominios (formato Tranco/Alexa: rank,domain) a MongoDB."""

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pymongo.errors import BulkWriteError

from .models import Site

CHUNK_SIZE = 5000


@dataclass
class ImportResult:
    read: int = 0
    imported: int = 0
    skipped_existing: int = 0


@dataclass
class TagResult:
    read: int = 0
    tagged: int = 0


def read_top_sites(csv_path: str | Path, limit: int | None = None) -> Iterator[tuple[int, str]]:
    """Lee un CSV `posicion,dominio` y devuelve tuplas (posicion, dominio)."""
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        count = 0
        for row in reader:
            if limit is not None and count >= limit:
                break
            if len(row) < 2:
                continue
            position_raw, url = row[0].strip(), row[1].strip()
            if not position_raw or not url:
                continue
            try:
                position = int(position_raw)
            except ValueError:
                continue
            count += 1
            yield position, url


def read_domains(path: str | Path) -> Iterator[str]:
    """Dominios de un fichero `posicion,dominio` o del listado RISP de Red.es (columnas separadas por `|`).
    De RISP solo se lee la primera columna (el dominio): nombre del titular e identificación se descartan."""
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                domain = line.split("|", 1)[0]
            else:
                parts = line.split(",")
                if len(parts) < 2:
                    continue
                domain = parts[1]
            domain = domain.strip().strip('"').strip().lower().rstrip(".")
            if domain and domain != "nombre_dominio":
                yield domain


def _known_urls() -> set[str]:
    """Dominios que ya hay en la BBDD, en cualquier lote."""
    return {d["url"] for d in Site._get_collection().find({}, {"url": 1, "_id": 0})}


def _import_unique(paths: list, limit: int | None, batch: int) -> "ImportResult":
    """Une varios ficheros en un lote sin repetir dominios: ni entre ficheros ni respecto a lo ya guardado."""
    result = ImportResult()
    seen = _known_urls()
    chunk: list[dict] = []
    now = datetime.now(timezone.utc)
    last = next(Site._get_collection().find({"batch": batch}, {"position": 1}).sort("position", -1).limit(1), None)
    position = (last or {}).get("position") or 0  # las altas continúan tras la última posición del lote
    for path in paths:
        for domain in read_domains(path):
            if limit is not None and result.read >= limit:
                break
            result.read += 1
            if domain in seen:
                result.skipped_existing += 1
                continue
            seen.add(domain)
            position += 1
            chunk.append({"url": domain, "position": position, "batch": batch, "retries": 0,
                          "finished": False, "last_search_datetime": now, "tech": []})
            if len(chunk) >= CHUNK_SIZE:
                inserted, skipped = _flush_chunk(chunk)
                result.imported += inserted
                result.skipped_existing += skipped
                chunk = []
    inserted, skipped = _flush_chunk(chunk)
    result.imported += inserted
    result.skipped_existing += skipped
    return result


def _flush_chunk(chunk: list[dict]) -> tuple[int, int]:
    """Inserta un bloque de documentos, ignorando duplicados por índice único `url`."""
    if not chunk:
        return 0, 0
    collection = Site._get_collection()
    try:
        res = collection.insert_many(chunk, ordered=False)
        return len(res.inserted_ids), len(chunk) - len(res.inserted_ids)
    except BulkWriteError as exc:
        write_errors = exc.details.get("writeErrors", [])
        duplicates = sum(1 for e in write_errors if e.get("code") == 11000)
        inserted = len(chunk) - len(write_errors)
        other_errors = len(write_errors) - duplicates
        if other_errors:
            raise
        return inserted, duplicates


def import_sites(csv_path, limit: int | None = None, batch: int = 1, unique: bool = False) -> ImportResult:
    """Importa sitios a la colección `Site` en bloques, en orden no-estricto para velocidad.
    Idempotente: las urls ya existentes (índice único) se omiten sin abortar el lote."""
    if unique:
        return _import_unique(csv_path if isinstance(csv_path, (list, tuple)) else [csv_path], limit, batch)
    result = ImportResult()
    chunk: list[dict] = []
    now = datetime.now(timezone.utc)

    for position, url in read_top_sites(csv_path, limit=limit):
        result.read += 1
        chunk.append(
            {
                "url": url,
                "position": position,
                "batch": batch,
                "retries": 0,
                "finished": False,
                "last_search_datetime": now,
                "tech": [],
            }
        )
        if len(chunk) >= CHUNK_SIZE:
            inserted, skipped = _flush_chunk(chunk)
            result.imported += inserted
            result.skipped_existing += skipped
            chunk = []

    inserted, skipped = _flush_chunk(chunk)
    result.imported += inserted
    result.skipped_existing += skipped
    return result


def tag_sites(path: str | Path, source: str, batch: int = 1) -> TagResult:
    """Añade `source` a `Site.sources` en los sitios del lote cuyo dominio aparece en el fichero.

    Idempotente (`$addToSet`) y sin escanear nada: sirve para saber de qué listado procede cada dominio.
    Los dominios del fichero que no están en el lote se ignoran. De un listado RISP solo se lee el dominio.
    """
    collection = Site._get_collection()
    result = TagResult()
    chunk: list[str] = []

    def flush() -> None:
        if chunk:
            update = collection.update_many({"batch": batch, "url": {"$in": chunk}}, {"$addToSet": {"sources": source}})
            result.tagged += update.matched_count
            chunk.clear()

    for domain in read_domains(path):
        result.read += 1
        chunk.append(domain)
        if len(chunk) >= CHUNK_SIZE:
            flush()
    flush()
    return result

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


def import_sites(csv_path: str | Path, limit: int | None = None, batch: int = 1) -> ImportResult:
    """Importa sitios a la colección `Site` en bloques, en orden no-estricto para velocidad.
    Idempotente: las urls ya existentes (índice único) se omiten sin abortar el lote."""
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

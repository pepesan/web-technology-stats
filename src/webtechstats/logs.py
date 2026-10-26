"""Log del CLI a fichero (con rotación) dentro de la carpeta de logs."""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILENAME = "webtechstats.log"
BATCH_COMMANDS = ("import-sites", "scan", "stats")
LOGGER_NAME = "webtechstats"
MAX_BYTES = 5 * 1024 * 1024
BACKUPS = 5


def log_filename(
    command: str, batch: int | None, now: datetime | None = None, shard: tuple[int, int] | None = None
) -> str:
    """Nombre del log de una ejecución: comando, lote y fecha/hora de lanzamiento.

    Ej.: `webtechstats_scan_batch-1_2026-10-25_20-15-03.log`. Sin lote en un comando que
    lo admite significa «todos los lotes» (`batch-all`)."""
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    if command in BATCH_COMMANDS:
        label = "batch-all" if batch is None else f"batch-{batch}"
        if shard:  # cada proceso hijo escribe en su propio fichero
            label += f"_shard-{shard[0] + 1}of{shard[1]}"
        return f"webtechstats_{command}_{label}_{stamp}.log"
    return f"webtechstats_{command}_{stamp}.log"


def setup_logging(directory: str | Path, level: str = "INFO", filename: str = LOG_FILENAME) -> Path:
    """Configura el logger `webtechstats` para escribir en `<directory>/<filename>`.

    Crea la carpeta si falta y es idempotente: reconfigurar sustituye el manejador anterior."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename

    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return path

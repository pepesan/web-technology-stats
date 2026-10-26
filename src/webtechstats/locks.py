# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Bloqueo de escaneos: dos `scan` sobre el mismo lote a la vez se pisarían (peticiones duplicadas).

Usa `flock` sobre ficheros dentro de la carpeta de logs: el sistema operativo libera el bloqueo cuando el
proceso muere (incluso con `kill -9`), así que nunca quedan bloqueos huérfanos.
"""

import fcntl
from contextlib import ExitStack, contextmanager
from pathlib import Path


class ScanAlreadyRunning(Exception):
    """Ya hay un escaneo en curso que afecta al mismo lote."""


def _acquire(handle, mode: int, message: str) -> None:
    try:
        fcntl.flock(handle, mode | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise ScanAlreadyRunning(message) from exc


@contextmanager
def scan_lock(directory: str | Path, batch: int | None):
    """Bloquea el escaneo de `batch` (None = todos los lotes).

    Un lote concreto toma un bloqueo compartido sobre «todos» y uno exclusivo propio, de modo que lotes
    distintos conviven, pero un escaneo de todos los lotes es incompatible con cualquier otro."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        everything = stack.enter_context(open(directory / "scan_all.lock", "a"))
        if batch is None:
            _acquire(everything, fcntl.LOCK_EX, "ya hay un escaneo en curso de algún lote: no se puede escanear todos a la vez")
        else:
            _acquire(everything, fcntl.LOCK_SH, "ya hay un escaneo en curso de todos los lotes")
            own = stack.enter_context(open(directory / f"scan_batch-{batch}.lock", "a"))
            _acquire(own, fcntl.LOCK_EX, f"ya hay un escaneo en curso del lote {batch}")
        yield

"""Escaneo en varios procesos: cada uno escanea un trozo disjunto (`position % n`) con sus propios hilos.

Los hilos de Python comparten el GIL: el análisis de las páginas (parseo HTML + regex) ocupa un solo núcleo
por proceso. Con varios procesos se usan varios núcleos sin coordinación entre ellos: los trozos no se
solapan y cada proceso guarda cada sitio al terminarlo, así que sigue siendo reanudable.
"""

import logging
import multiprocessing
import os
import queue as queue_module
import signal
import threading
import time
from dataclasses import asdict

from .detection import ScanResult, scan_pending_sites

logger = logging.getLogger(__name__)
_children: list = []


class ShardFailed(Exception):
    """Algún proceso hijo terminó con error. `partial` recoge lo que sí se completó."""

    def __init__(self, message: str, partial: ScanResult):
        super().__init__(message)
        self.partial = partial


def split_limit(total: int, parts: int, index: int) -> int:
    """Reparte `total` sitios entre `parts` procesos sin perder ni añadir ninguno."""
    base, remainder = divmod(total, parts)
    return base + (1 if index < remainder else 0)


def kill_children() -> None:
    """Mata de inmediato a los hijos (segunda señal del usuario)."""
    for child in _children:
        if child.is_alive():
            child.kill()


def child_main(shard: int, total: int, kwargs: dict, result_queue) -> None:
    """Proceso hijo: escanea el trozo `shard` de `total`."""
    from .config import MongoConfig
    from .db import init_db
    from .logs import log_filename, setup_logging
    from .models import Site
    from .wappalyzer import Wappalyzer

    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):  # parada ordenada: se guardan los sitios en vuelo
        signal.signal(sig, lambda *_: stop.set())
    init_db(MongoConfig.load(kwargs.get("config_path")))
    Site.ensure_schema()
    setup_logging(kwargs["log_dir"], kwargs["log_level"], log_filename("scan", kwargs["batch"], shard=(shard, total)))
    log = logging.getLogger("webtechstats.parallel")
    log.info("Trozo %d/%d: límite %s, %s hilos", shard + 1, total, kwargs["limit"], kwargs["workers"])

    def progress(partial) -> None:
        if partial.processed % 100 == 0:
            log.info("trozo %d/%d: … %d procesados (OK: %d, fallidos: %d)", shard + 1, total,
                     partial.processed, partial.ok, partial.failed)

    result = scan_pending_sites(
        limit=kwargs["limit"],
        wappalyzer=Wappalyzer.latest(),
        batch=kwargs["batch"],
        workers=kwargs["workers"],
        progress=progress,
        max_retries=kwargs["max_retries"],
        retry_failed=kwargs["retry_failed"],
        should_stop=stop.is_set,
        shard=(shard, total),
    )
    log.info("trozo %d/%d: Procesados: %d | OK: %d | Fallidos: %d", shard + 1, total,
             result.processed, result.ok, result.failed)
    result_queue.put((shard, asdict(result)))


def run_sharded(
    processes: int,
    kwargs: dict,
    child_target=child_main,
    stop_event: threading.Event | None = None,
    poll: float = 0.2,
) -> ScanResult:
    """Lanza `processes` hijos y suma sus resultados. Si `stop_event` se activa, reenvía SIGTERM a los hijos
    (parada ordenada) y espera a que guarden lo que tienen en vuelo."""
    if processes < 2:
        raise ValueError("run_sharded necesita al menos 2 procesos")
    ctx = multiprocessing.get_context("spawn")  # nada de fork con hilos ni conexiones abiertas
    result_queue = ctx.Queue()
    _children.clear()
    for index in range(processes):
        child_kwargs = dict(kwargs, limit=split_limit(kwargs["limit"], processes, index))
        _children.append(ctx.Process(target=child_target, args=(index, processes, child_kwargs, result_queue)))
    for child in _children:
        child.start()

    results: dict[int, dict] = {}

    def drain() -> None:
        while True:
            try:
                shard, payload = result_queue.get_nowait()
            except queue_module.Empty:
                return
            if "ready" not in payload:
                results[shard] = payload

    forwarded = False
    try:
        while any(child.is_alive() for child in _children):
            drain()
            if stop_event is not None and stop_event.is_set() and not forwarded:
                forwarded = True
                for child in _children:
                    if child.is_alive():
                        os.kill(child.pid, signal.SIGTERM)
            time.sleep(poll)
        for child in _children:
            child.join()
        time.sleep(0.2)
        drain()
    finally:
        kill_children()

    total = ScanResult()
    for payload in results.values():
        total.processed += payload.get("processed", 0)
        total.ok += payload.get("ok", 0)
        total.failed += payload.get("failed", 0)
        total.stopped = total.stopped or bool(payload.get("stopped"))
    crashed = [i for i, child in enumerate(_children) if child.exitcode != 0 and i not in results]
    if crashed:
        raise ShardFailed(f"los procesos de los trozos {[i + 1 for i in crashed]} terminaron con error", total)
    return total

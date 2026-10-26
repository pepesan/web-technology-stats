"""Hijos falsos para probar la orquestación multiproceso sin MongoDB (importables desde `spawn`)."""

import signal
import sys
import time


def quick(shard, total, kwargs, queue):
    """Devuelve como «procesados» el límite que le tocó, para comprobar el reparto."""
    queue.put((shard, {"processed": kwargs["limit"], "ok": kwargs["limit"], "failed": shard, "stopped": False}))


def until_signalled(shard, total, kwargs, queue):
    stopping = []
    signal.signal(signal.SIGTERM, lambda *_: stopping.append(1))
    queue.put((shard, {"ready": True}))
    while not stopping:
        time.sleep(0.05)
    queue.put((shard, {"processed": 5, "ok": 5, "failed": 0, "stopped": True}))


def crash_on_shard_1(shard, total, kwargs, queue):
    if shard == 1:
        sys.exit(3)
    queue.put((shard, {"processed": 4, "ok": 4, "failed": 0, "stopped": False}))

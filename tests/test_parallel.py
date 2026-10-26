# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
import signal
import threading
import time

import pytest

from webtechstats.parallel import ShardFailed, run_sharded, split_limit

KW = {"limit": 100, "batch": 1}


def test_split_limit_distributes_the_total_without_losing_or_adding_sites():
    for total in (0, 1, 7, 100, 1001):
        for parts in (1, 2, 3, 16):
            shares = [split_limit(total, parts, i) for i in range(parts)]
            assert sum(shares) == total
            assert max(shares) - min(shares) <= 1


def test_run_sharded_runs_every_shard_and_each_gets_its_share_of_the_limit():
    import fake_children

    result = run_sharded(3, {"limit": 100, "batch": 1}, child_target=fake_children.quick)
    assert result.processed == 100          # 34 + 33 + 33: el límite total se reparte sin perder ni añadir
    assert result.ok == 100
    assert result.failed == 0 + 1 + 2       # suma de los 3 hijos
    assert result.stopped is False


def test_stop_event_forwards_sigterm_to_children_and_collects_their_results():
    import fake_children

    stop = threading.Event()
    threading.Timer(2.0, stop.set).start()  # el «usuario» pide parar cuando los hijos ya están en marcha
    started = time.monotonic()
    result = run_sharded(3, KW, child_target=fake_children.until_signalled, stop_event=stop)
    assert result.stopped is True
    assert result.processed == 15
    assert time.monotonic() - started < 15


def test_a_crashed_child_is_reported_without_hanging_the_others():
    import fake_children

    with pytest.raises(ShardFailed, match=r"\[2\]"):
        run_sharded(3, KW, child_target=fake_children.crash_on_shard_1)


def test_single_process_is_rejected():
    with pytest.raises(ValueError):
        run_sharded(1, KW)

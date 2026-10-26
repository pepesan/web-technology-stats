import os
import signal
import subprocess
import sys
import time

import pytest
from click.testing import CliRunner

from webtechstats import cli
from webtechstats.locks import ScanAlreadyRunning, scan_lock


def test_same_batch_cannot_be_scanned_twice_at_once(tmp_path):
    with scan_lock(tmp_path, 1):
        with pytest.raises(ScanAlreadyRunning, match="lote 1"):
            with scan_lock(tmp_path, 1):
                pass


def test_different_batches_can_run_in_parallel(tmp_path):
    with scan_lock(tmp_path, 1):
        with scan_lock(tmp_path, 2):
            pass


def test_scanning_all_batches_conflicts_with_any_batch_and_vice_versa(tmp_path):
    with scan_lock(tmp_path, 1):
        with pytest.raises(ScanAlreadyRunning):
            with scan_lock(tmp_path, None):
                pass
    with scan_lock(tmp_path, None):
        with pytest.raises(ScanAlreadyRunning):
            with scan_lock(tmp_path, 2):
                pass


def test_lock_is_released_on_exit_even_after_an_error(tmp_path):
    with pytest.raises(RuntimeError):
        with scan_lock(tmp_path, 1):
            raise RuntimeError("fallo")
    with scan_lock(tmp_path, 1):
        pass


def test_lock_is_released_when_the_holder_is_killed(tmp_path):
    """Un proceso muerto con kill -9 no deja un bloqueo huérfano."""
    code = (
        "import sys, time\n"
        "from webtechstats.locks import scan_lock\n"
        f"with scan_lock({str(tmp_path)!r}, 1):\n"
        "    print('listo', flush=True); time.sleep(60)\n"
    )
    holder = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "listo"
        with pytest.raises(ScanAlreadyRunning):
            with scan_lock(tmp_path, 1):
                pass
        os.kill(holder.pid, signal.SIGKILL)
        holder.wait(timeout=10)
        with scan_lock(tmp_path, 1):
            pass
    finally:
        holder.kill()


def test_cli_scan_refuses_to_start_if_the_batch_is_already_being_scanned(tmp_path, monkeypatch):
    import mongomock

    from webtechstats.db import init_db

    monkeypatch.setenv("WTS_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "_connect", lambda: init_db(mongo_client_class=mongomock.MongoClient))
    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: object()))
    called = []
    monkeypatch.setattr(cli, "scan_pending_sites", lambda **kw: called.append(kw))
    with scan_lock(tmp_path, 4):
        result = CliRunner().invoke(cli.main, ["scan", "--batch", "4"])
    assert result.exit_code != 0
    assert "ya hay un escaneo" in result.output
    assert called == []

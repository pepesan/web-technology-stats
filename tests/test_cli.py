# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
import mongomock
import pytest
from click.testing import CliRunner

from webtechstats import cli
from webtechstats.models import Site


@pytest.fixture(autouse=True)
def mock_connection(monkeypatch):
    """Los comandos abren/cierran su propia conexión: se redirige a mongomock."""
    from webtechstats.db import init_db

    monkeypatch.setattr(cli, "_connect", lambda: init_db(mongo_client_class=mongomock.MongoClient))
    monkeypatch.setattr(cli, "ping", lambda: True)


def run(*args):
    return CliRunner().invoke(cli.main, list(args))


def test_help_lists_commands():
    result = run("--help")
    assert result.exit_code == 0
    for cmd in ("init-db", "import-sites", "scan", "stats", "detect"):
        assert cmd in result.output


def test_init_db_ok():
    result = run("init-db")
    assert result.exit_code == 0
    assert "Conexión OK" in result.output


def test_init_db_fails_without_connection(monkeypatch):
    monkeypatch.setattr(cli, "ping", lambda: False)
    result = run("init-db")
    assert result.exit_code == 1


def test_import_then_stats(csv_file):
    result = run("import-sites", "--file", str(csv_file), "--limit", "3")
    assert result.exit_code == 0, result.output
    assert "Importados: 3" in result.output
    # la conexión se cierra al terminar: el segundo comando abre la suya (mongomock nuevo)
    stats = run("stats")
    assert stats.exit_code == 0
    assert "Total:" in stats.output


def test_import_requires_existing_file():
    assert run("import-sites", "--file", "/no/existe.csv").exit_code != 0


def test_scan_reports_counts(monkeypatch):
    from webtechstats.detection import ScanResult

    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: object()))
    monkeypatch.setattr(cli, "scan_pending_sites", lambda limit, wappalyzer, batch, workers, progress, max_retries, retry_failed, should_stop: ScanResult(3, 2, 1))
    result = run("scan", "--limit", "3")
    assert result.exit_code == 0
    assert "Procesados: 3 | OK: 2 | Fallidos: 1" in result.output


def test_detect_prints_technologies(monkeypatch):
    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: object()))
    monkeypatch.setattr("webtechstats.detection.detect_technologies", lambda url, wappalyzer: ["Nginx", "PHP"])
    result = run("detect", "x.com")
    assert result.exit_code == 0
    assert result.output.split() == ["Nginx", "PHP"]


def test_detect_unreachable_exits_1(monkeypatch):
    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: object()))
    monkeypatch.setattr("webtechstats.detection.detect_technologies", lambda url, wappalyzer: None)
    assert run("detect", "x.com").exit_code == 1


def test_connect_uses_config_option(tmp_path, monkeypatch):
    """`--config` llega hasta MongoConfig.load a través del contexto de click."""
    seen = {}
    monkeypatch.undo()  # quita el _connect simulado del fixture autouse
    monkeypatch.setattr(cli, "ping", lambda: True)
    monkeypatch.setattr(cli, "init_db", lambda config: seen.setdefault("cfg", config))
    monkeypatch.setattr(cli, "close_db", lambda: None)
    monkeypatch.delenv("MONGO_HOST", raising=False)
    cfg_file = tmp_path / "c.toml"
    cfg_file.write_text('[mongo]\nhost = "desde-fichero"\n')

    monkeypatch.setattr("webtechstats.models.Site.ensure_schema", classmethod(lambda cls: None))
    result = run("--config", str(cfg_file), "init-db")

    assert result.exit_code == 0, result.output
    assert seen["cfg"].host == "desde-fichero"


def test_missing_config_file_is_clean_error(monkeypatch):
    monkeypatch.undo()
    result = run("--config", "/no/existe.toml", "init-db")
    assert result.exit_code != 0
    assert "No existe el fichero de configuración" in result.output


# --- scan --workers: CLI > env > fichero > defecto (4) ---


@pytest.fixture
def scan_spy(monkeypatch, tmp_path):
    """Aísla la configuración y captura los `workers` con que se invoca el escaneo."""
    from webtechstats.detection import ScanResult

    for var in ("SCAN_WORKERS", "WEBTECHSTATS_CONFIG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("webtechstats.config.DEFAULT_CONFIG_PATHS", (tmp_path / "nohay.toml",))
    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: object()))
    seen = {}

    def fake(limit, wappalyzer, batch, workers, progress, max_retries, retry_failed, should_stop):
        seen["workers"] = workers
        seen["max_retries"] = max_retries
        seen["retry_failed"] = retry_failed
        seen["should_stop"] = should_stop
        return ScanResult(0, 0, 0)

    monkeypatch.setattr(cli, "scan_pending_sites", fake)
    return seen, tmp_path


def test_scan_workers_default_is_4(scan_spy):
    seen, _ = scan_spy
    assert run("scan").exit_code == 0
    assert seen["workers"] == 4


def test_scan_workers_from_config_file(scan_spy):
    seen, tmp = scan_spy
    cfg = tmp / "c.toml"
    cfg.write_text("[scan]\nworkers = 6\n")
    assert run("--config", str(cfg), "scan").exit_code == 0
    assert seen["workers"] == 6


def test_scan_workers_option_beats_config_file(scan_spy):
    seen, tmp = scan_spy
    cfg = tmp / "c.toml"
    cfg.write_text("[scan]\nworkers = 6\n")
    assert run("--config", str(cfg), "scan", "--workers", "1").exit_code == 0
    assert seen["workers"] == 1


def test_scan_workers_option_beats_env(scan_spy, monkeypatch):
    seen, _ = scan_spy
    monkeypatch.setenv("SCAN_WORKERS", "9")
    assert run("scan", "--workers", "3").exit_code == 0
    assert seen["workers"] == 3


def test_scan_rejects_invalid_workers_option(scan_spy):
    assert run("scan", "--workers", "0").exit_code != 0


def test_scan_invalid_config_value_is_clean_error(scan_spy):
    _, tmp = scan_spy
    cfg = tmp / "c.toml"
    cfg.write_text("[scan]\nworkers = 0\n")
    result = run("--config", str(cfg), "scan")
    assert result.exit_code != 0
    assert "workers" in result.output


def test_scan_max_retries_default_config_and_option(scan_spy):
    seen, tmp = scan_spy
    assert run("scan").exit_code == 0
    assert seen["max_retries"] == 10
    cfg = tmp / "c.toml"
    cfg.write_text("[scan]\nmax_retries = 5\n")
    assert run("--config", str(cfg), "scan").exit_code == 0
    assert seen["max_retries"] == 5
    assert run("--config", str(cfg), "scan", "--max-retries", "1").exit_code == 0
    assert seen["max_retries"] == 1


def test_scan_rejects_invalid_max_retries_option(scan_spy):
    assert run("scan", "--max-retries", "0").exit_code != 0


def test_scan_does_not_retry_failed_by_default_and_flag_enables_it(scan_spy):
    seen, _ = scan_spy
    assert run("scan").exit_code == 0
    assert seen["retry_failed"] is False
    assert run("scan", "--retry-failed").exit_code == 0
    assert seen["retry_failed"] is True


def test_scan_stops_gracefully_on_sigterm_and_restores_handlers(scan_spy, monkeypatch):
    import os
    import signal

    from webtechstats.detection import ScanResult

    seen, _ = scan_spy
    before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}

    def fake(limit, wappalyzer, batch, workers, progress, max_retries, retry_failed, should_stop):
        assert should_stop() is False
        os.kill(os.getpid(), signal.SIGTERM)  # el proceso recibe la señal de parada
        seen["stop_after_signal"] = should_stop()
        return ScanResult(5, 5, 0, stopped=True)

    monkeypatch.setattr(cli, "scan_pending_sites", fake)
    result = run("scan")

    assert result.exit_code == 0
    assert seen["stop_after_signal"] is True
    assert "Interrumpido" in result.output
    assert {s: signal.getsignal(s) for s in before} == before


def test_second_signal_aborts_immediately_without_waiting_for_workers(scan_spy, monkeypatch):
    import os
    import signal

    seen, _ = scan_spy
    exits = []

    def fake_exit(code):
        exits.append(code)
        raise RuntimeError("abortado")

    monkeypatch.setattr(cli.os, "_exit", fake_exit)

    def fake(limit, wappalyzer, batch, workers, progress, max_retries, retry_failed, should_stop):
        os.kill(os.getpid(), signal.SIGTERM)  # 1.ª: parada ordenada
        assert should_stop() is True
        os.kill(os.getpid(), signal.SIGTERM)  # 2.ª: aborta sin esperar a los hilos
        raise AssertionError("no debería llegar aquí")

    monkeypatch.setattr(cli, "scan_pending_sites", fake)
    run("scan")
    assert exits == [130]


# --- scan --processes: varios procesos, cada uno con sus hilos ---


@pytest.fixture
def sharded_spy(scan_spy, monkeypatch):
    from webtechstats.detection import ScanResult

    seen, tmp = scan_spy
    calls = []

    def fake_run_sharded(processes, kwargs, stop_event=None, **_):
        calls.append({"processes": processes, "kwargs": kwargs, "stop_event": stop_event})
        return ScanResult(7, 6, 1)

    monkeypatch.setattr(cli, "run_sharded", fake_run_sharded)
    return calls, seen, tmp


def test_scan_is_single_process_by_default(sharded_spy):
    calls, seen, _ = sharded_spy
    assert run("scan").exit_code == 0
    assert calls == [] and "workers" in seen  # camino en proceso, sin hijos


def test_scan_with_processes_delegates_to_run_sharded_with_the_effective_settings(sharded_spy):
    calls, _, _ = sharded_spy
    result = run("scan", "--limit", "50", "--batch", "3", "--processes", "4", "--workers", "8")
    assert result.exit_code == 0, result.output
    (call,) = calls
    assert call["processes"] == 4
    kw = call["kwargs"]
    assert (kw["limit"], kw["batch"], kw["workers"], kw["max_retries"], kw["retry_failed"]) == (50, 3, 8, 10, False)
    assert {"log_dir", "log_level", "config_path"} <= set(kw)
    assert "Procesados: 7 | OK: 6 | Fallidos: 1" in result.output
    assert "4 proceso(s)" in result.output


def test_processes_from_config_and_the_option_wins(sharded_spy):
    calls, _, tmp = sharded_spy
    cfg = tmp / "c.toml"
    cfg.write_text("[scan]\nprocesses = 3\nworkers = 5\n")
    run("--config", str(cfg), "scan")
    assert calls[-1]["processes"] == 3 and calls[-1]["kwargs"]["workers"] == 5
    assert calls[-1]["kwargs"]["config_path"] == str(cfg)
    run("--config", str(cfg), "scan", "--processes", "2")
    assert calls[-1]["processes"] == 2


def test_processes_option_is_validated(sharded_spy):
    assert run("scan", "--processes", "0").exit_code != 0


def test_a_failed_shard_is_reported_with_the_partial_result_and_exit_code_1(sharded_spy, monkeypatch):
    from webtechstats.detection import ScanResult
    from webtechstats.parallel import ShardFailed

    def boom(processes, kwargs, stop_event=None, **_):
        raise ShardFailed("los procesos de los trozos [2] terminaron con error", ScanResult(4, 4, 0))

    monkeypatch.setattr(cli, "run_sharded", boom)
    result = run("scan", "--processes", "3")
    assert result.exit_code == 1
    assert "trozos [2]" in result.output and "Procesados: 4" in result.output


def test_signal_sets_the_stop_event_passed_to_the_children(sharded_spy, monkeypatch):
    import os
    import signal

    from webtechstats.detection import ScanResult

    calls, _, _ = sharded_spy

    def fake_run_sharded(processes, kwargs, stop_event=None, **_):
        os.kill(os.getpid(), signal.SIGTERM)
        assert stop_event.is_set()
        return ScanResult(3, 3, 0, stopped=True)

    monkeypatch.setattr(cli, "run_sharded", fake_run_sharded)
    result = run("scan", "--processes", "2")
    assert result.exit_code == 0 and "Interrumpido" in result.output


def test_second_signal_kills_the_children_before_exiting(sharded_spy, monkeypatch):
    import os
    import signal

    killed, exits = [], []
    monkeypatch.setattr(cli, "kill_children", lambda: killed.append(1))

    def fake_exit(code):
        exits.append(code)
        raise RuntimeError("abortado")

    monkeypatch.setattr(cli.os, "_exit", fake_exit)

    def fake_run_sharded(processes, kwargs, stop_event=None, **_):
        os.kill(os.getpid(), signal.SIGTERM)
        os.kill(os.getpid(), signal.SIGTERM)

    monkeypatch.setattr(cli, "run_sharded", fake_run_sharded)
    run("scan", "--processes", "2")
    assert killed == [1] and exits == [130]

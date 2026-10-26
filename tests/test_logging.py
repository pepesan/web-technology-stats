import logging

import mongomock
import pytest
from click.testing import CliRunner

from webtechstats import cli
from webtechstats.config import ConfigError, LogConfig
from webtechstats.logs import LOG_FILENAME, log_filename, setup_logging


@pytest.fixture(autouse=True)
def reset_logging():
    yield
    logging.getLogger("webtechstats").handlers.clear()


@pytest.fixture
def log_env(monkeypatch, tmp_path):
    for var in ("WTS_LOG_DIR", "WTS_LOG_LEVEL", "WEBTECHSTATS_CONFIG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("webtechstats.config.DEFAULT_CONFIG_PATHS", (tmp_path / "nohay.toml",))
    return tmp_path


# --- LogConfig ---


def test_log_config_defaults(log_env):
    cfg = LogConfig.load()
    assert (cfg.dir, cfg.level) == ("logs", "INFO")


def test_log_config_file_env_and_validation(log_env, monkeypatch):
    f = log_env / "c.toml"
    f.write_text('[log]\ndir = "mis_logs"\nlevel = "debug"\n')
    assert LogConfig.load(f) == LogConfig(dir="mis_logs", level="DEBUG")
    monkeypatch.setenv("WTS_LOG_DIR", "otro")
    assert LogConfig.load(f).dir == "otro"
    f.write_text('[log]\nlevel = "ruidoso"\n')
    with pytest.raises(ConfigError, match="level"):
        LogConfig.load(f)


# --- setup_logging ---


def test_setup_creates_directory_and_file(log_env):
    path = setup_logging(log_env / "sub" / "logs", "INFO")
    logging.getLogger("webtechstats.x").info("hola mundo")
    assert path == log_env / "sub" / "logs" / LOG_FILENAME
    text = path.read_text()
    assert "hola mundo" in text and "INFO" in text and "webtechstats.x" in text


def test_setup_is_idempotent_and_does_not_duplicate_lines(log_env):
    setup_logging(log_env, "INFO")
    path = setup_logging(log_env, "INFO")
    logging.getLogger("webtechstats").info("una sola vez")
    assert path.read_text().count("una sola vez") == 1


def test_level_filters_messages(log_env):
    path = setup_logging(log_env, "WARNING")
    log = logging.getLogger("webtechstats")
    log.info("no debería salir")
    log.warning("sí debería salir")
    text = path.read_text()
    assert "no debería salir" not in text and "sí debería salir" in text


# --- el CLI escribe en el log ---


@pytest.fixture
def cli_db(monkeypatch):
    from webtechstats.db import init_db

    monkeypatch.setattr(cli, "_connect", lambda: init_db(mongo_client_class=mongomock.MongoClient))
    monkeypatch.setattr(cli, "ping", lambda: True)


def test_cli_logs_import_to_file(log_env, cli_db, csv_file):
    result = CliRunner().invoke(cli.main, ["import-sites", "--file", str(csv_file), "--limit", "3"])
    assert result.exit_code == 0, result.output
    (log_file,) = (log_env / "logs").glob("webtechstats_import-sites_batch-1_*.log")
    text = log_file.read_text()
    assert "import-sites" in text
    assert "Importados: 3" in text


def test_cli_log_dir_comes_from_config_and_level_option(log_env, cli_db, csv_file):
    cfg = log_env / "c.toml"
    cfg.write_text('[log]\ndir = "otra_carpeta"\n')
    CliRunner().invoke(cli.main, ["--config", str(cfg), "--log-level", "DEBUG", "import-sites", "--file", str(csv_file)])
    assert len(list((log_env / "otra_carpeta").glob("webtechstats_import-sites_batch-1_*.log"))) == 1
    assert not (log_env / "logs").exists()


def test_cli_invalid_log_level_option_is_rejected(log_env):
    assert CliRunner().invoke(cli.main, ["--log-level", "ruidoso", "stats"]).exit_code != 0


def test_scan_logs_sites_and_summary(log_env, cli_db, monkeypatch):
    import responses

    from webtechstats.models import Site

    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: __import__("webtechstats.wappalyzer", fromlist=["x"]).Wappalyzer({}, {})))
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://vivo.com", body="<html></html>")
        for url in ("https://muerto.com", "http://muerto.com", "https://www.muerto.com"):
            rsps.add(responses.GET, url, body=ConnectionError("down"))
        runner = CliRunner()
        monkeypatch.setattr(cli, "scan_pending_sites", __import__("webtechstats.detection", fromlist=["x"]).scan_pending_sites)
        cli._connect()
        Site(url="vivo.com", position=1).save()
        Site(url="muerto.com", position=2).save()
        result = runner.invoke(cli.main, ["--log-level", "DEBUG", "scan", "--limit", "10", "--workers", "2"])
    assert result.exit_code == 0, result.output
    (log_file,) = (log_env / "logs").glob("webtechstats_scan_batch-all_*.log")
    text = log_file.read_text()
    assert "vivo.com" in text and "muerto.com" in text
    assert "Procesados: 2 | OK: 1 | Fallidos: 1" in text


# --- nombre del fichero de log: comando + lote + fecha de lanzamiento ---

from datetime import datetime

NOW = datetime(2026, 10, 25, 20, 15, 3)


def test_log_filename_includes_command_batch_and_launch_time():
    assert log_filename("scan", 1, NOW) == "webtechstats_scan_batch-1_2026-10-25_20-15-03.log"
    assert log_filename("import-sites", 12, NOW) == "webtechstats_import-sites_batch-12_2026-10-25_20-15-03.log"


def test_log_filename_without_batch_means_all_batches():
    assert log_filename("scan", None, NOW) == "webtechstats_scan_batch-all_2026-10-25_20-15-03.log"
    assert log_filename("stats", None, NOW) == "webtechstats_stats_batch-all_2026-10-25_20-15-03.log"


def test_log_filename_for_commands_without_batch_has_no_batch_part():
    assert log_filename("init-db", None, NOW) == "webtechstats_init-db_2026-10-25_20-15-03.log"
    assert log_filename("detect", None, NOW) == "webtechstats_detect_2026-10-25_20-15-03.log"


def test_cli_scan_log_is_named_after_its_batch(log_env, cli_db, monkeypatch):
    monkeypatch.setattr(cli.Wappalyzer, "latest", classmethod(lambda cls: object()))
    from webtechstats.detection import ScanResult

    monkeypatch.setattr(cli, "scan_pending_sites", lambda **kw: ScanResult(0, 0, 0))
    CliRunner().invoke(cli.main, ["scan", "--batch", "7"])
    assert len(list((log_env / "logs").glob("webtechstats_scan_batch-7_????-??-??_??-??-??.log"))) == 1


def test_each_launch_goes_to_its_own_file(log_env, cli_db, csv_file, monkeypatch):
    names = iter(["a", "b"])
    monkeypatch.setattr(cli, "log_filename", lambda command, batch: f"webtechstats_{next(names)}.log")
    for _ in range(2):
        CliRunner().invoke(cli.main, ["import-sites", "--file", str(csv_file)])
    assert sorted(p.name for p in (log_env / "logs").iterdir()) == ["webtechstats_a.log", "webtechstats_b.log"]

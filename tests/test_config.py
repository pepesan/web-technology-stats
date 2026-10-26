from pathlib import Path

from webtechstats.config import MongoConfig


def test_defaults_match_compose(monkeypatch):
    for var in ("MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PASSWORD", "MONGO_DB", "MONGO_AUTH_SOURCE"):
        monkeypatch.delenv(var, raising=False)
    cfg = MongoConfig.from_env()
    assert (cfg.host, cfg.port, cfg.db, cfg.auth_source) == ("localhost", 27017, "webstats", "admin")


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("MONGO_HOST", "db.local")
    monkeypatch.setenv("MONGO_PORT", "27999")
    monkeypatch.setenv("MONGO_DB", "otra")
    cfg = MongoConfig.from_env()
    assert cfg.host == "db.local"
    assert cfg.port == 27999
    assert isinstance(cfg.port, int)
    assert cfg.db == "otra"


import pytest

from webtechstats.config import ConfigError


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for var in ("MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PASSWORD", "MONGO_DB",
                "MONGO_AUTH_SOURCE", "WEBTECHSTATS_CONFIG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)  # sin ./webtechstats.toml
    monkeypatch.setattr("webtechstats.config.DEFAULT_CONFIG_PATHS", (tmp_path / "nohay.toml",))
    return tmp_path


def write_cfg(path, body):
    path.write_text(body)
    return path


def test_load_without_file_uses_defaults(clean_env):
    assert MongoConfig.load() == MongoConfig()


def test_load_from_explicit_file(clean_env):
    cfg_file = write_cfg(clean_env / "c.toml", '[mongo]\nhost = "db.x"\nport = 1234\npassword = "s3"\n')
    cfg = MongoConfig.load(cfg_file)
    assert (cfg.host, cfg.port, cfg.password, cfg.db) == ("db.x", 1234, "s3", "webstats")


def test_env_overrides_file(clean_env, monkeypatch):
    cfg_file = write_cfg(clean_env / "c.toml", '[mongo]\nhost = "db.x"\nport = 1234\n')
    monkeypatch.setenv("MONGO_HOST", "desde-env")
    cfg = MongoConfig.load(cfg_file)
    assert (cfg.host, cfg.port) == ("desde-env", 1234)


def test_config_found_via_env_var(clean_env, monkeypatch):
    cfg_file = write_cfg(clean_env / "otro.toml", '[mongo]\ndb = "viaenv"\n')
    monkeypatch.setenv("WEBTECHSTATS_CONFIG", str(cfg_file))
    assert MongoConfig.load().db == "viaenv"


def test_config_found_in_default_location(clean_env, monkeypatch):
    cfg_file = write_cfg(clean_env / "default.toml", '[mongo]\ndb = "pordefecto"\n')
    monkeypatch.setattr("webtechstats.config.DEFAULT_CONFIG_PATHS", (cfg_file,))
    assert MongoConfig.load().db == "pordefecto"


def test_missing_explicit_file_is_error(clean_env):
    with pytest.raises(ConfigError):
        MongoConfig.load(clean_env / "nope.toml")


def test_invalid_toml_and_unknown_keys_are_errors(clean_env):
    with pytest.raises(ConfigError, match="TOML inválido"):
        MongoConfig.load(write_cfg(clean_env / "a.toml", "[mongo\n"))
    with pytest.raises(ConfigError, match="desconocidas"):
        MongoConfig.load(write_cfg(clean_env / "b.toml", '[mongo]\nhots = "typo"\n'))


def test_example_file_is_valid_and_matches_defaults(clean_env):
    example = Path(__file__).resolve().parent.parent / "webtechstats.example.toml"
    assert MongoConfig.load(example) == MongoConfig()


# --- [scan] workers: defecto 4, fichero < variable de entorno ---

from webtechstats.config import ScanConfig


def test_scan_workers_default_is_4(clean_env):
    assert ScanConfig.load().workers == 4
    assert ScanConfig().workers == 4


def test_scan_workers_from_file(clean_env):
    cfg_file = write_cfg(clean_env / "c.toml", "[scan]\nworkers = 8\n")
    assert ScanConfig.load(cfg_file).workers == 8


def test_scan_workers_env_overrides_file(clean_env, monkeypatch):
    cfg_file = write_cfg(clean_env / "c.toml", "[scan]\nworkers = 8\n")
    monkeypatch.setenv("SCAN_WORKERS", "2")
    assert ScanConfig.load(cfg_file).workers == 2


def test_scan_and_mongo_sections_coexist(clean_env):
    cfg_file = write_cfg(clean_env / "c.toml", '[mongo]\nhost = "h"\n\n[scan]\nworkers = 6\n')
    assert MongoConfig.load(cfg_file).host == "h"
    assert ScanConfig.load(cfg_file).workers == 6


@pytest.mark.parametrize("bad", ["0", "-3", '"mucho"', "2.5"])
def test_scan_workers_must_be_positive_integer(clean_env, bad):
    cfg_file = write_cfg(clean_env / "c.toml", f"[scan]\nworkers = {bad}\n")
    with pytest.raises(ConfigError, match="workers"):
        ScanConfig.load(cfg_file)


def test_scan_unknown_key_is_error(clean_env):
    with pytest.raises(ConfigError, match="desconocidas"):
        ScanConfig.load(write_cfg(clean_env / "c.toml", "[scan]\nworkerz = 4\n"))


def test_example_file_scan_section_matches_defaults(clean_env):
    example = Path(__file__).resolve().parent.parent / "webtechstats.example.toml"
    assert ScanConfig.load(example) == ScanConfig()


# --- [scan] max_retries: defecto 3 ---


def test_scan_max_retries_default_is_10(clean_env):
    assert ScanConfig.load().max_retries == 10


def test_scan_max_retries_from_file_and_env(clean_env, monkeypatch):
    cfg_file = write_cfg(clean_env / "c.toml", "[scan]\nmax_retries = 5\n")
    assert ScanConfig.load(cfg_file).max_retries == 5
    monkeypatch.setenv("SCAN_MAX_RETRIES", "1")
    assert ScanConfig.load(cfg_file).max_retries == 1


@pytest.mark.parametrize("bad", ["0", "-1", '"x"'])
def test_scan_max_retries_must_be_positive_integer(clean_env, bad):
    cfg_file = write_cfg(clean_env / "c.toml", f"[scan]\nmax_retries = {bad}\n")
    with pytest.raises(ConfigError, match="max_retries"):
        ScanConfig.load(cfg_file)


# --- [scan] processes ---


def test_scan_processes_default_file_env_and_validation(clean_env, monkeypatch):
    assert ScanConfig.load().processes == 1
    cfg_file = write_cfg(clean_env / "c.toml", "[scan]\nprocesses = 8\n")
    assert ScanConfig.load(cfg_file).processes == 8
    monkeypatch.setenv("SCAN_PROCESSES", "4")
    assert ScanConfig.load(cfg_file).processes == 4
    monkeypatch.delenv("SCAN_PROCESSES")
    with pytest.raises(ConfigError, match="processes"):
        ScanConfig.load(write_cfg(clean_env / "d.toml", "[scan]\nprocesses = 0\n"))


# --- [mongo] max_pool_size: pool de conexiones acotado por proceso ---


def test_mongo_max_pool_size_default_file_env_and_validation(clean_env, monkeypatch):
    assert MongoConfig.load().max_pool_size == 10
    cfg_file = write_cfg(clean_env / "c.toml", "[mongo]\nmax_pool_size = 25\n")
    assert MongoConfig.load(cfg_file).max_pool_size == 25
    monkeypatch.setenv("MONGO_MAX_POOL_SIZE", "5")
    assert MongoConfig.load(cfg_file).max_pool_size == 5
    monkeypatch.delenv("MONGO_MAX_POOL_SIZE")
    for bad in ("0", "-1", '"muchas"'):
        with pytest.raises(ConfigError, match="max_pool_size"):
            MongoConfig.load(write_cfg(clean_env / "d.toml", f"[mongo]\nmax_pool_size = {bad}\n"))

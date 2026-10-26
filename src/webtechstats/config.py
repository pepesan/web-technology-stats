"""Configuración: conexión a MongoDB (`[mongo]`) y escaneo (`[scan]`).

Precedencia (de menor a mayor): valores por defecto < fichero TOML < variables de entorno
(`MONGO_*`, `SCAN_WORKERS`, `SCAN_PROCESSES`, `SCAN_MAX_RETRIES`). En el CLI, los parámetros de línea de comandos (p. ej.
`scan --workers`) tienen prioridad sobre todo lo anterior.

El fichero se busca, por este orden, en:
  1. la ruta indicada explícitamente (`--config` en el CLI)
  2. la variable de entorno `WEBTECHSTATS_CONFIG`
  3. `./webtechstats.toml`
  4. `~/.config/webtechstats/config.toml`
"""

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

CONFIG_ENV_VAR = "WEBTECHSTATS_CONFIG"
DEFAULT_CONFIG_PATHS = (
    Path("webtechstats.toml"),
    Path("~/.config/webtechstats/config.toml").expanduser(),
)

_ENV_VARS = {
    "host": "MONGO_HOST",
    "port": "MONGO_PORT",
    "db": "MONGO_DB",
    "username": "MONGO_USER",
    "password": "MONGO_PASSWORD",
    "auth_source": "MONGO_AUTH_SOURCE",
    "max_pool_size": "MONGO_MAX_POOL_SIZE",
}


class ConfigError(Exception):
    """Fichero de configuración inexistente o inválido."""


def find_config_file(path: str | Path | None = None) -> Path | None:
    """Devuelve el fichero de configuración a usar, o None si no hay ninguno."""
    if path is not None:
        explicit = Path(path).expanduser()
        if not explicit.is_file():
            raise ConfigError(f"No existe el fichero de configuración: {explicit}")
        return explicit
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return find_config_file(env_path)
    return next((p for p in DEFAULT_CONFIG_PATHS if p.is_file()), None)


def _read_section(path: str | Path | None, section: str, allowed: set[str]) -> dict:
    """Devuelve la tabla `[section]` del fichero de configuración ({} si no hay fichero o tabla)."""
    config_file = find_config_file(path)
    if config_file is None:
        return {}
    try:
        with open(config_file, "rb") as fh:
            values = tomllib.load(fh).get(section, {})
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{config_file}: TOML inválido: {exc}") from exc
    unknown = set(values) - allowed
    if unknown:
        raise ConfigError(f"{config_file}: claves desconocidas en [{section}]: {', '.join(sorted(unknown))}")
    return values


@dataclass(frozen=True)
class MongoConfig:
    host: str = "localhost"
    port: int = 27017
    db: str = "webstats"
    username: str = "mongodbuser"
    password: str = "mongodbuser"
    auth_source: str = "admin"
    max_pool_size: int = 10  # conexiones máximas por proceso (pymongo permite 100 por defecto)

    @classmethod
    def from_env(cls) -> "MongoConfig":
        """Solo valores por defecto + variables de entorno (sin fichero)."""
        return cls._build({})

    @classmethod
    def load(cls, path: str | Path | None = None) -> "MongoConfig":
        """Defaults + fichero TOML (si existe) + variables de entorno."""
        return cls._build(_read_section(path, "mongo", {f.name for f in fields(cls)}))

    @classmethod
    def _build(cls, file_values: dict) -> "MongoConfig":
        merged = {}
        for f in fields(cls):
            value = os.environ.get(_ENV_VARS[f.name], file_values.get(f.name, f.default))
            if f.name == "port":
                merged[f.name] = int(value)
            elif f.name == "max_pool_size":
                merged[f.name] = _positive_int(value, f.name)
            else:
                merged[f.name] = str(value)
        return cls(**merged)


@dataclass(frozen=True)
class ScanConfig:
    workers: int = 4  # peticiones HTTP simultáneas
    processes: int = 1  # procesos en paralelo (cada uno con `workers` hilos): usa varios núcleos
    max_retries: int = 10  # un sitio que falla tantas veces deja de reintentarse

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ScanConfig":
        """Defaults + fichero TOML (`[scan]`) + variable de entorno `SCAN_WORKERS`."""
        values = _read_section(path, "scan", {f.name for f in fields(cls)})
        workers = os.environ.get("SCAN_WORKERS", values.get("workers", cls.workers))
        max_retries = os.environ.get("SCAN_MAX_RETRIES", values.get("max_retries", cls.max_retries))
        processes = os.environ.get("SCAN_PROCESSES", values.get("processes", cls.processes))
        return cls(
            workers=_positive_int(workers, "workers"),
            max_retries=_positive_int(max_retries, "max_retries"),
            processes=_positive_int(processes, "processes"),
        )


def _positive_int(value, name: str) -> int:
    if isinstance(value, bool) or (isinstance(value, float)) or not str(value).strip().lstrip("-").isdigit():
        raise ConfigError(f"{name} debe ser un entero positivo (recibido: {value!r})")
    number = int(value)
    if number < 1:
        raise ConfigError(f"{name} debe ser un entero positivo (recibido: {value!r})")
    return number


LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass(frozen=True)
class LogConfig:
    dir: str = "logs"  # relativo al directorio de trabajo
    level: str = "INFO"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "LogConfig":
        """Defaults + fichero TOML (`[log]`) + variables `WTS_LOG_DIR` / `WTS_LOG_LEVEL`."""
        values = _read_section(path, "log", {f.name for f in fields(cls)})
        directory = os.environ.get("WTS_LOG_DIR", values.get("dir", cls.dir))
        level = str(os.environ.get("WTS_LOG_LEVEL", values.get("level", cls.level))).upper()
        if level not in LOG_LEVELS:
            raise ConfigError(f"level debe ser uno de {', '.join(LOG_LEVELS)} (recibido: {level!r})")
        return cls(dir=str(directory), level=level)

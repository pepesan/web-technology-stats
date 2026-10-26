# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Conexión perezosa a MongoDB (no se conecta al importar el módulo)."""

from mongoengine import connect, disconnect, get_connection

from .config import MongoConfig


def init_db(config: MongoConfig | None = None, alias: str = "default", mongo_client_class=None):
    """Conecta a MongoDB y devuelve el cliente. Idempotente para el mismo alias."""
    config = config or MongoConfig.load()
    kwargs = dict(
        db=config.db,
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        authentication_source=config.auth_source,
        maxPoolSize=config.max_pool_size,
        alias=alias,
        uuidRepresentation="standard",
    )
    if mongo_client_class is not None:
        kwargs["mongo_client_class"] = mongo_client_class
    return connect(**kwargs)


def close_db(alias: str = "default") -> None:
    disconnect(alias=alias)


def ping(alias: str = "default") -> bool:
    try:
        get_connection(alias=alias).admin.command("ping")
        return True
    except Exception:
        return False

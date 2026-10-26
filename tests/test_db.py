from webtechstats import db
from webtechstats.config import MongoConfig


def test_init_db_bounds_the_connection_pool(monkeypatch):
    """Cada proceso usa pocas conexiones: sin tope, pymongo permite hasta 100 por proceso."""
    seen = {}
    monkeypatch.setattr(db, "connect", lambda **kwargs: seen.update(kwargs))
    db.init_db(MongoConfig(max_pool_size=7))
    assert seen["maxPoolSize"] == 7
    db.init_db(MongoConfig())
    assert seen["maxPoolSize"] == 10

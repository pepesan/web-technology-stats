# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
import mongomock
import pytest

from webtechstats.db import close_db, init_db
from webtechstats.models import Site


@pytest.fixture
def db():
    """Conexión mongoengine sobre mongomock (sin MongoDB real), limpia en cada test."""
    close_db()
    init_db(mongo_client_class=mongomock.MongoClient)
    Site.drop_collection()
    Site.ensure_schema()
    yield
    Site.drop_collection()
    close_db()


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "top.csv"
    path.write_text("1,google.com\n2,example.org\n3,wordpress.org\n4,python.org\n5,mozilla.org\n")
    return path


@pytest.fixture(autouse=True)
def isolated_log_dir(tmp_path, monkeypatch):
    """Los tests del CLI no deben escribir en el ./logs real del repositorio."""
    monkeypatch.setenv("WTS_LOG_DIR", str(tmp_path / "logs"))

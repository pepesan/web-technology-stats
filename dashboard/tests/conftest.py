# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
import mongomock
import pytest
from fastapi.testclient import TestClient
from webtechstats.db import close_db, init_db
from webtechstats.models import Site
from wts_dashboard.app import create_app


@pytest.fixture
def db():
    close_db()
    init_db(mongo_client_class=mongomock.MongoClient)
    Site.drop_collection()
    Site.ensure_schema()
    yield
    Site.drop_collection()
    close_db()


@pytest.fixture
def client(db):
    return TestClient(create_app(connect=False, cache_ttl=0, frontend_dist=None))


def seed():
    Site(url="a.com", position=1, batch=1, finished=True, tech=["PHP", "MySQL", "jQuery", "Nginx"]).save()
    Site(url="b.com", position=2, batch=1, finished=True, tech=["PHP", "React", "TypeScript", "Laravel"]).save()
    Site(url="c.com", position=3, batch=1, finished=True, tech=["Python", "PostgreSQL", "Vue.js"]).save()
    Site(url="d.com", position=4, batch=1, finished=False).save()
    Site(url="a.com", position=1, batch=2, finished=True, tech=["Go", "Redis"]).save()

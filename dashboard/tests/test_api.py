# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
from conftest import seed
from webtechstats.models import Site


def test_topics_lists_all_topics(client):
    data = client.get("/api/topics").json()
    assert list(data) == ["lang_back", "lang_front", "back_libs", "front_libs", "databases", "other"]


def test_batches(client):
    seed()
    data = client.get("/api/batches").json()
    assert [(b["batch"], b["total"], b["finished"], b["failed"]) for b in data] == [(1, 4, 3, 0), (2, 1, 1, 0)]
    assert all(b["last_activity"] for b in data)


def test_overview_all_batches(client):
    seed()
    data = client.get("/api/overview").json()
    assert (data["total"], data["finished"], data["pending"]) == (5, 4, 1)
    by_key = {t["key"]: t for t in data["topics"]}
    assert by_key["lang_back"]["top"][0] == {"tech": "PHP", "count": 2, "pct": 50.0}


def test_overview_single_batch(client):
    seed()
    data = client.get("/api/overview", params={"batch": 2}).json()
    assert (data["total"], data["finished"], data["distinct_tech"]) == (1, 1, 2)


def test_topic_ranking_groups_by_topic(client):
    seed()
    back = client.get("/api/topics/lang_back", params={"batch": 1}).json()
    assert [i["tech"] for i in back["items"]][:2] == ["PHP", "Python"]
    assert back["base"] == 3 and back["items"][0]["pct"] == 66.7
    assert "TypeScript" not in [i["tech"] for i in back["items"]]

    front_lang = client.get("/api/topics/lang_front", params={"batch": 1}).json()
    assert [i["tech"] for i in front_lang["items"]] == ["TypeScript"]

    dbs = client.get("/api/topics/databases", params={"batch": 1}).json()
    assert {i["tech"] for i in dbs["items"]} == {"MySQL", "PostgreSQL"}

    front = client.get("/api/topics/front_libs", params={"batch": 1}).json()
    assert {"React", "jQuery", "Vue.js"} <= {i["tech"] for i in front["items"]}

    back_libs = client.get("/api/topics/back_libs", params={"batch": 1}).json()
    assert "Laravel" in [i["tech"] for i in back_libs["items"]]

    other = client.get("/api/topics/other", params={"batch": 1}).json()
    assert [i["tech"] for i in other["items"]] == ["Nginx"]
    assert other["items"][0]["category"] == "Web servers"
    assert other["categories"] == ["Web servers"]


def test_topic_ranking_limit_and_category(client):
    seed()
    data = client.get("/api/topics/front_libs", params={"batch": 1, "limit": 1}).json()
    assert len(data["items"]) == 1 and data["total_items"] >= 3
    cat = data["categories"][0]
    filtered = client.get("/api/topics/front_libs", params={"batch": 1, "category": cat}).json()
    assert all(i["category"] == cat for i in filtered["items"])


def test_unknown_topic_is_404(client):
    assert client.get("/api/topics/nope").status_code == 404


def test_limit_is_validated(client):
    assert client.get("/api/topics/other", params={"limit": 0}).status_code == 422
    assert client.get("/api/topics/other", params={"limit": 9999}).status_code == 422


def test_empty_database(client):
    data = client.get("/api/overview").json()
    assert data["total"] == 0 and data["with_tech"] == 0
    assert client.get("/api/topics/other").json()["items"] == []


def test_serves_frontend_with_spa_fallback(db, tmp_path):
    from fastapi.testclient import TestClient
    from wts_dashboard.app import create_app

    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>vue</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    c = TestClient(create_app(connect=False, frontend_dist=tmp_path))
    assert c.get("/").text == "<html>vue</html>"
    assert c.get("/ruta/cliente").text == "<html>vue</html>"
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/api/topics").status_code == 200
    assert c.get("/../../etc/passwd").text == "<html>vue</html>"


def test_overview_separates_unanswered_from_pending(client):
    from webtechstats.models import Site

    Site(url="ok.com", position=1, batch=1, finished=True, tech=["PHP"]).save()
    Site(url="nuevo.com", position=2, batch=1).save()
    Site(url="muerto.com", position=3, batch=1, retries=2).save()
    data = client.get("/api/overview").json()
    assert (data["total"], data["finished"], data["failed"], data["pending"]) == (3, 1, 1, 1)
    assert client.get("/api/batches").json()[0]["failed"] == 1


def test_overview_limited_to_top_positions(client):
    seed()
    data = client.get("/api/overview", params={"batch": 1, "max_position": 2}).json()
    assert (data["total"], data["finished"], data["pending"]) == (2, 2, 0)
    assert data["max_position"] == 2
    assert client.get("/api/overview", params={"batch": 1}).json()["max_position"] is None


def test_topic_ranking_limited_to_top_positions(client):
    seed()
    back = client.get("/api/topics/lang_back", params={"batch": 1, "max_position": 2}).json()
    assert back["base"] == 2 and [i["tech"] for i in back["items"]] == ["PHP"]
    assert back["max_position"] == 2


def test_max_position_must_be_positive(client):
    assert client.get("/api/overview", params={"max_position": 0}).status_code == 422


def test_config_json_tells_the_frontend_to_use_the_api(client):
    assert client.get("/config.json").json() == {"source": "api"}


def test_overview_and_ranking_filtered_by_tld(client):
    Site(url="a.es", position=1, batch=1, finished=True, tech=["PHP", "MySQL"]).save()
    Site(url="b.com", position=2, batch=1, finished=True, tech=["Go"]).save()
    data = client.get("/api/overview", params={"batch": 1, "tld": "es"}).json()
    assert (data["total"], data["finished"], data["tld"]) == (1, 1, "es")
    back = client.get("/api/topics/lang_back", params={"batch": 1, "tld": "es"}).json()
    assert [i["tech"] for i in back["items"]] == ["PHP"] and back["tld"] == "es"
    assert client.get("/api/overview", params={"tld": "e s"}).status_code == 422

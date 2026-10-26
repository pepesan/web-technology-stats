from webtechstats.models import Site


def test_new_site_is_not_discarded(db):
    site = Site(url="a.com", position=1).save()
    assert site.discarded is False
    assert site.discard_reason is None


def test_ensure_schema_marks_old_failures_as_discarded(db):
    """Los fallos anteriores al campo `discarded` (retries > 0 sin marca) se marcan al migrar."""
    collection = Site._get_collection()
    collection.insert_many([
        {"url": "viejo.com", "batch": 1, "position": 1, "retries": 2, "finished": False, "tech": []},
        {"url": "nuevo.com", "batch": 1, "position": 2, "retries": 0, "finished": False, "tech": []},
        {"url": "ok.com", "batch": 1, "position": 3, "retries": 1, "finished": True, "tech": ["PHP"]},
    ])
    Site.ensure_schema()
    assert Site.objects.get(url="viejo.com").discarded is True
    assert Site.objects.get(url="viejo.com").discard_reason == "desconocido"
    assert Site.objects.get(url="nuevo.com").discarded is False
    assert Site.objects.get(url="ok.com").discarded is False
    Site.ensure_schema()  # idempotente
    assert Site.objects(discarded=True).count() == 1

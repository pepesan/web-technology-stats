# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
from webtechstats.importer import import_sites, read_top_sites
from webtechstats.models import Site


def test_read_top_sites_parses_and_limits(csv_file):
    assert list(read_top_sites(csv_file, limit=2)) == [(1, "google.com"), (2, "example.org")]
    assert len(list(read_top_sites(csv_file))) == 5


def test_read_top_sites_skips_malformed_rows(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("1,a.com\n\nsolo\nx,b.com\n3,\n4,d.com\n")
    assert list(read_top_sites(path)) == [(1, "a.com"), (4, "d.com")]


def test_import_sites_inserts_pending_sites(db, csv_file):
    result = import_sites(csv_file, batch=7)
    assert (result.read, result.imported, result.skipped_existing) == (5, 5, 0)
    site = Site.objects.get(url="google.com")
    assert site.position == 1
    assert site.batch == 7
    assert site.finished is False
    assert site.tech == []


def test_import_sites_is_idempotent(db, csv_file):
    import_sites(csv_file)
    result = import_sites(csv_file)
    assert (result.imported, result.skipped_existing) == (0, 5)
    assert Site.objects.count() == 5


def test_import_sites_respects_limit(db, csv_file):
    result = import_sites(csv_file, limit=3)
    assert result.imported == 3
    assert Site.objects.count() == 3


def test_import_sites_multiple_chunks(db, tmp_path, monkeypatch):
    monkeypatch.setattr("webtechstats.importer.CHUNK_SIZE", 2)
    path = tmp_path / "n.csv"
    path.write_text("".join(f"{i},site{i}.com\n" for i in range(1, 8)))
    assert import_sites(path).imported == 7
    assert Site.objects.count() == 7


def test_same_urls_in_new_batch_are_stored_separately(db, csv_file):
    import_sites(csv_file, batch=1)
    result = import_sites(csv_file, batch=2)
    assert (result.imported, result.skipped_existing) == (5, 0)
    assert Site.objects.count() == 10
    assert Site.objects(batch=1).count() == 5
    assert Site.objects(batch=2).count() == 5


def test_ensure_schema_migrates_legacy_unique_url_index(db):
    collection = Site._get_collection()
    collection.drop_indexes()
    collection.create_index("url", unique=True)  # esquema antiguo
    Site.ensure_schema()
    info = collection.index_information()
    assert "url_1" not in info
    Site(url="a.com", position=1, batch=1).save()
    Site(url="a.com", position=1, batch=2).save()
    assert Site.objects(url="a.com").count() == 2

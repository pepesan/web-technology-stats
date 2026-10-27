# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
from webtechstats.importer import import_sites, read_top_sites, tag_sites
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


# ---------- importación única de varios ficheros (dominios .es) ----------


def _write(path, text):
    path.write_text(text)
    return path


def test_unique_import_merges_files_without_repeating_domains(db, tmp_path):
    cc = _write(tmp_path / "cc.csv", "1,a.es\n2,b.es\n3,A.es\n")
    risp = _write(tmp_path / "risp.csv", '"NOMBRE_DOMINIO"|"NOMBRE_TITULAR"|"IDENTIFICACION"\n'
                                         '"b.es"|"Titular S.L."|"B123"\n"c.es"|"Otro"|"X1"\n')
    result = import_sites([cc, risp], batch=3, unique=True)
    assert sorted(s.url for s in Site.objects(batch=3)) == ["a.es", "b.es", "c.es"]
    assert (result.imported, result.skipped_existing) == (3, 2)
    assert sorted(s.position for s in Site.objects(batch=3)) == [1, 2, 3]  # posición = orden de aparición


def test_unique_import_skips_domains_already_in_any_batch(db, tmp_path):
    import_sites(_write(tmp_path / "top.csv", "1,google.es\n2,x.com\n"), batch=1)
    new = _write(tmp_path / "nuevo.csv", "1,google.es\n2,nuevo.es\n")
    result = import_sites([new], batch=3, unique=True)
    assert [s.url for s in Site.objects(batch=3)] == ["nuevo.es"]
    assert result.imported == 1 and result.skipped_existing == 1


def test_unique_import_is_idempotent(db, tmp_path):
    f = _write(tmp_path / "a.csv", "1,a.es\n2,b.es\n")
    import_sites([f], batch=3, unique=True)
    assert import_sites([f], batch=3, unique=True).imported == 0
    assert Site.objects.count() == 2


def test_risp_holder_data_is_never_stored(db, tmp_path):
    risp = _write(tmp_path / "r.csv", '"NOMBRE_DOMINIO"|"NOMBRE_TITULAR"|"IDENTIFICACION"\n'
                                      '"x.es"|"Persona Fisica"|"12345678Z"\n')
    import_sites([risp], batch=4, unique=True)
    raw = str(Site._get_collection().find_one({"url": "x.es"}))
    assert "Persona" not in raw and "12345678Z" not in raw


def test_unique_import_continues_positions_after_the_batch_maximum(db, tmp_path):
    import_sites(_write(tmp_path / "top.csv", "1,a.com\n2,b.com\n"), batch=1)
    import_sites([_write(tmp_path / "es.csv", "1,c.es\n2,d.es\n")], batch=1, unique=True)
    assert {s.url: s.position for s in Site.objects(batch=1)} == {"a.com": 1, "b.com": 2, "c.es": 3, "d.es": 4}


# ---------- etiquetado de fuentes (campo `sources`) ----------


def test_tag_sites_marks_only_the_matching_sites_of_the_batch(db, tmp_path):
    import_sites(_write(tmp_path / "a.csv", "1,a.es\n2,b.es\n3,c.es\n"), batch=1)
    import_sites(_write(tmp_path / "b.csv", "1,a.es\n"), batch=2)
    lista = _write(tmp_path / "risp.csv", '"NOMBRE_DOMINIO"|"NOMBRE_TITULAR"|"IDENTIFICACION"\n"A.es"|"x"|"y"\n"c.es"|"x"|"y"\n"fuera.es"|"x"|"y"\n')
    result = tag_sites(lista, "risp2026", batch=1)
    assert (result.read, result.tagged) == (3, 2)  # fuera.es no está en el lote: se ignora
    assert {s.url: list(s.sources) for s in Site.objects(batch=1)} == {"a.es": ["risp2026"], "b.es": [], "c.es": ["risp2026"]}
    assert list(Site.objects.get(url="a.es", batch=2).sources) == []  # otro lote: intacto


def test_tag_sites_is_idempotent_and_accumulates_sources(db, tmp_path):
    import_sites(_write(tmp_path / "a.csv", "1,a.es\n2,b.es\n"), batch=1)
    f = _write(tmp_path / "f.csv", "1,a.es\n")
    tag_sites(f, "cc", batch=1)
    tag_sites(f, "cc", batch=1)
    tag_sites(_write(tmp_path / "g.csv", "1,a.es\n2,b.es\n"), "tranco", batch=1)
    assert sorted(Site.objects.get(url="a.es").sources) == ["cc", "tranco"]
    assert list(Site.objects.get(url="b.es").sources) == ["tranco"]


def test_tag_sites_never_stores_risp_holder_data(db, tmp_path):
    import_sites(_write(tmp_path / "a.csv", "1,x.es\n"), batch=1)
    risp = _write(tmp_path / "r.csv", '"NOMBRE_DOMINIO"|"NOMBRE_TITULAR"|"IDENTIFICACION"\n"x.es"|"Persona Fisica"|"12345678Z"\n')
    tag_sites(risp, "risp2026", batch=1)
    raw = str(Site._get_collection().find_one({"url": "x.es"}))
    assert "Persona" not in raw and "12345678Z" not in raw

# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
from webtechstats.models import Site
from webtechstats.stats import source_overlap, summary, top_technologies


def seed():
    Site(url="a.com", position=1, finished=True, tech=["PHP", "WordPress"]).save()
    Site(url="b.com", position=2, finished=True, tech=["PHP"]).save()
    Site(url="c.com", position=3, finished=True, tech=[]).save()
    Site(url="d.com", position=4, finished=False, tech=["Ignorada"]).save()


def test_summary(db):
    seed()
    assert summary() == {"total": 4, "finished": 3, "pending": 1, "failed": 0, "finished_with_tech": 2}


def test_summary_empty(db):
    assert summary() == {"total": 0, "finished": 0, "pending": 0, "failed": 0, "finished_with_tech": 0}


def test_top_technologies_counts_only_finished_sites(db):
    seed()
    assert top_technologies(top=10) == [
        {"tech": "PHP", "count": 2},
        {"tech": "WordPress", "count": 1},
    ]


def test_top_technologies_respects_limit(db):
    seed()
    assert top_technologies(top=1) == [{"tech": "PHP", "count": 2}]


def test_stats_filtered_by_batch(db):
    Site(url="a.com", position=1, batch=1, finished=True, tech=["PHP"]).save()
    Site(url="a.com", position=1, batch=2, finished=True, tech=["Go"]).save()
    Site(url="b.com", position=2, batch=2, finished=False).save()
    assert summary(batch=2) == {"total": 2, "finished": 1, "pending": 1, "failed": 0, "finished_with_tech": 1}
    assert summary()["total"] == 3
    assert top_technologies(batch=1) == [{"tech": "PHP", "count": 1}]
    assert {r["tech"] for r in top_technologies()} == {"PHP", "Go"}


def test_summary_separates_unanswered_from_pending(db):
    Site(url="ok.com", position=1, finished=True, tech=["PHP"]).save()
    Site(url="nuevo.com", position=2).save()                       # nunca intentado
    Site(url="muerto.com", position=3, retries=2).save()           # intentado sin éxito
    Site(url="muerto2.com", position=4, retries=1).save()
    assert summary() == {"total": 4, "finished": 1, "pending": 1, "failed": 2, "finished_with_tech": 1}
    # analizados + sin respuesta + pendientes = total
    s = summary()
    assert s["finished"] + s["failed"] + s["pending"] == s["total"]


def test_stats_filtered_by_max_position(db):
    seed()
    Site(url="e.com", position=5, finished=False, retries=1).save()
    assert summary(max_position=2) == {"total": 2, "finished": 2, "pending": 0, "failed": 0, "finished_with_tech": 2}
    assert summary(max_position=5)["failed"] == 1
    assert top_technologies(max_position=1) == [{"tech": "PHP", "count": 1}, {"tech": "WordPress", "count": 1}]
    assert top_technologies(max_position=None) == top_technologies()


def test_max_position_combines_with_batch(db):
    Site(url="a.com", position=1, batch=1, finished=True, tech=["PHP"]).save()
    Site(url="b.com", position=9, batch=1, finished=True, tech=["Go"]).save()
    Site(url="a.com", position=1, batch=2, finished=True, tech=["Rust"]).save()
    assert summary(batch=1, max_position=5)["total"] == 1
    assert top_technologies(batch=1, max_position=5) == [{"tech": "PHP", "count": 1}]


def seed_tlds():
    Site(url="a.es", position=1, finished=True, tech=["PHP", "MySQL"]).save()
    Site(url="b.com", position=2, finished=True, tech=["Go"]).save()
    Site(url="c.es", position=3, finished=False, retries=1).save()
    Site(url="d.es", position=5, finished=False).save()
    Site(url="es.com", position=6, finished=True, tech=["Rust"]).save()  # contiene "es" pero no termina en .es
    Site(url="e.co.es", position=7, finished=True, tech=["PHP"]).save()


def test_summary_and_ranking_filtered_by_tld(db):
    seed_tlds()
    assert summary(tld="es") == {"total": 4, "finished": 2, "pending": 1, "failed": 1, "finished_with_tech": 2}
    assert top_technologies(tld="es") == [{"tech": "PHP", "count": 2}, {"tech": "MySQL", "count": 1}]
    assert summary()["total"] == 6


def test_tld_combines_with_batch_and_max_position(db):
    seed_tlds()
    assert summary(tld="es", max_position=1)["total"] == 1
    assert top_technologies(tld="es", max_position=1) == [{"tech": "MySQL", "count": 1}, {"tech": "PHP", "count": 1}]
    assert summary(tld="es", batch=2)["total"] == 0


def test_tld_is_matched_literally_not_as_a_regex(db):
    seed_tlds()
    assert summary(tld=".*")["total"] == 0


def seed_sources():
    Site(url="a.es", position=1, finished=True, tech=["PHP"], sources=["tranco", "risp2026"]).save()
    Site(url="b.es", position=2, finished=True, tech=["Go"], sources=["risp2026", "cc"]).save()
    Site(url="c.es", position=3, finished=False, retries=1, sources=["risp2026"]).save()
    Site(url="d.es", position=4, finished=True, tech=["Rust"], sources=["risp2020"]).save()
    Site(url="e.com", position=5, finished=True, tech=["PHP"], sources=["tranco"]).save()
    Site(url="f.com", position=6, finished=True, tech=["Java"]).save()  # sin etiquetar


def test_summary_and_ranking_filtered_by_source(db):
    seed_sources()
    assert summary(source="risp2026") == {"total": 3, "finished": 2, "pending": 0, "failed": 1, "finished_with_tech": 2}
    assert summary(source="tranco")["total"] == 2
    assert summary(source="nadie")["total"] == 0
    assert summary()["total"] == 6  # sin filtro de fuente cuenta todo
    assert {r["tech"] for r in top_technologies(source="risp2026")} == {"PHP", "Go"}
    assert top_technologies(source="risp2020") == [{"tech": "Rust", "count": 1}]


def test_source_filter_combines_with_batch_position_and_tld(db):
    seed_sources()
    Site(url="a.es", position=1, batch=2, finished=True, tech=["Zig"], sources=["risp2026"]).save()
    assert summary(batch=1, source="risp2026")["total"] == 3
    assert summary(batch=1, source="risp2026", max_position=2)["total"] == 2
    assert summary(batch=1, source="tranco", tld="es")["total"] == 1
    assert top_technologies(batch=2, source="risp2026") == [{"tech": "Zig", "count": 1}]


def test_source_overlap_counts_each_set_of_sources_regardless_of_order(db):
    seed_sources()
    Site(url="g.es", position=7, finished=True, sources=["cc", "risp2026"]).save()  # mismo conjunto que b.es, otro orden
    Site(url="h.es", position=8, batch=2, finished=True, sources=["cc"]).save()      # otro lote: no cuenta
    # primero los conjuntos más frecuentes; a igual cuenta, por orden alfabético de las fuentes
    assert source_overlap(batch=1) == [
        {"sources": ["cc", "risp2026"], "count": 2},
        {"sources": [], "count": 1},
        {"sources": ["risp2020"], "count": 1},
        {"sources": ["risp2026"], "count": 1},
        {"sources": ["risp2026", "tranco"], "count": 1},
        {"sources": ["tranco"], "count": 1},
    ]

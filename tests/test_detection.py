# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
import json

import pytest
import responses

from webtechstats.detection import detect_technologies, scan_pending_sites
from webtechstats.models import Site
from webtechstats.wappalyzer import Wappalyzer

APPS = {
    "Nginx": {"cats": [22], "headers": {"Server": "nginx"}},
    "WordPress": {"cats": [1], "meta": {"generator": "WordPress"}, "implies": ["PHP"]},
    "PHP": {"cats": [27]},
}


@pytest.fixture
def wappalyzer():
    return Wappalyzer({}, json.loads(json.dumps(APPS)))


WP_HTML = '<html><head><meta name="generator" content="WordPress 6.5"></head></html>'


@responses.activate
def test_detect_uses_first_responding_variant(wappalyzer):
    responses.add(responses.GET, "https://ok.com", body=WP_HTML, headers={"Server": "nginx"})
    assert detect_technologies("ok.com", wappalyzer) == ["Nginx", "PHP", "WordPress"]
    assert len(responses.calls) == 1


@responses.activate
def test_detect_falls_back_to_http_then_www(wappalyzer):
    responses.add(responses.GET, "https://fb.com", body=ConnectionError("down"))
    responses.add(responses.GET, "http://fb.com", body=ConnectionError("down"))
    responses.add(responses.GET, "https://www.fb.com", body=WP_HTML)
    assert detect_technologies("fb.com", wappalyzer) == ["PHP", "WordPress"]
    assert [c.request.url for c in responses.calls] == [
        "https://fb.com/", "http://fb.com/", "https://www.fb.com/",
    ]


@responses.activate
def test_detect_returns_none_when_unreachable(wappalyzer):
    for url in ("https://dead.com", "http://dead.com", "https://www.dead.com"):
        responses.add(responses.GET, url, body=ConnectionError("down"))
    assert detect_technologies("dead.com", wappalyzer) is None


@responses.activate
def test_scan_updates_sites_in_position_order_with_limit(db, wappalyzer):
    Site(url="b.com", position=2).save()
    Site(url="a.com", position=1).save()
    Site(url="c.com", position=3).save()
    responses.add(responses.GET, "https://a.com", body=WP_HTML)
    responses.add(responses.GET, "https://b.com", body="<html></html>")

    result = scan_pending_sites(limit=2, wappalyzer=wappalyzer)

    assert (result.processed, result.ok, result.failed) == (2, 2, 0)
    a = Site.objects.get(url="a.com")
    assert a.finished is True and a.tech == ["PHP", "WordPress"]
    b = Site.objects.get(url="b.com")
    assert b.finished is True and b.tech == []
    assert Site.objects.get(url="c.com").finished is False


@responses.activate
def test_scan_counts_failures_and_increments_retries(db, wappalyzer):
    Site(url="dead.com", position=1).save()
    for url in ("https://dead.com", "http://dead.com", "https://www.dead.com"):
        responses.add(responses.GET, url, body=ConnectionError("down"))

    result = scan_pending_sites(limit=10, wappalyzer=wappalyzer)

    assert (result.processed, result.ok, result.failed) == (1, 0, 1)
    site = Site.objects.get(url="dead.com")
    assert site.finished is False
    assert site.retries == 1


def test_scan_skips_finished_sites(db, wappalyzer):
    Site(url="done.com", position=1, finished=True, tech=["X"]).save()
    assert scan_pending_sites(limit=10, wappalyzer=wappalyzer).processed == 0


@responses.activate
def test_scan_with_batch_leaves_other_batches_untouched(db, wappalyzer):
    Site(url="a.com", position=1, batch=1, finished=True, tech=["Viejo"]).save()
    Site(url="a.com", position=1, batch=2).save()
    responses.add(responses.GET, "https://a.com", body=WP_HTML)

    result = scan_pending_sites(limit=10, wappalyzer=wappalyzer, batch=2)

    assert result.processed == 1
    assert Site.objects.get(url="a.com", batch=1).tech == ["Viejo"]
    assert Site.objects.get(url="a.com", batch=2).tech == ["PHP", "WordPress"]


@responses.activate
def test_scan_without_batch_covers_all_batches(db, wappalyzer):
    Site(url="a.com", position=1, batch=1).save()
    Site(url="b.com", position=2, batch=2).save()
    responses.add(responses.GET, "https://a.com", body=WP_HTML)
    responses.add(responses.GET, "https://b.com", body=WP_HTML)
    assert scan_pending_sites(limit=10, wappalyzer=wappalyzer).processed == 2


@responses.activate
def test_parallel_scan_processes_everything_and_reports_progress(db, wappalyzer):
    for i in range(1, 13):
        Site(url=f"s{i}.com", position=i).save()
        if i == 7:  # uno inalcanzable
            for url in ("https://s7.com", "http://s7.com", "https://www.s7.com"):
                responses.add(responses.GET, url, body=ConnectionError("down"))
        else:
            responses.add(responses.GET, f"https://s{i}.com", body=WP_HTML)
    seen = []

    result = scan_pending_sites(limit=100, wappalyzer=wappalyzer, workers=4, progress=lambda r: seen.append(r.processed))

    assert (result.processed, result.ok, result.failed) == (12, 11, 1)
    assert seen == list(range(1, 13))
    assert Site.objects(finished=True).count() == 11
    assert Site.objects.get(url="s7.com").retries == 1
    assert Site.objects.get(url="s1.com").tech == ["PHP", "WordPress"]


@responses.activate
def test_scan_skips_sites_that_reached_max_retries(db, wappalyzer):
    Site(url="agotado.com", position=1, retries=3).save()
    Site(url="reintentable.com", position=2, retries=2).save()
    Site(url="nuevo.com", position=3, retries=0).save()
    for url in ("https://reintentable.com", "https://nuevo.com"):
        responses.add(responses.GET, url, body=WP_HTML)

    result = scan_pending_sites(limit=10, wappalyzer=wappalyzer, max_retries=3, retry_failed=True)

    assert (result.processed, result.ok) == (2, 2)
    assert Site.objects.get(url="agotado.com").retries == 3  # ni se intentó
    assert [c.request.url for c in responses.calls] == ["https://reintentable.com/", "https://nuevo.com/"]


@responses.activate
def test_scan_without_max_retries_has_no_limit(db, wappalyzer):
    Site(url="agotado.com", position=1, retries=50).save()
    responses.add(responses.GET, "https://agotado.com", body=WP_HTML)
    assert scan_pending_sites(limit=10, wappalyzer=wappalyzer, retry_failed=True).processed == 1


@responses.activate
def test_failure_increments_retries_until_it_is_skipped(db, wappalyzer):
    Site(url="muerto.com", position=1).save()
    for url in ("https://muerto.com", "http://muerto.com", "https://www.muerto.com"):
        responses.add(responses.GET, url, body=ConnectionError("down"))
    processed = [scan_pending_sites(limit=10, wappalyzer=wappalyzer, max_retries=2, retry_failed=True).processed for _ in range(4)]
    assert processed == [1, 1, 0, 0]
    assert Site.objects.get(url="muerto.com").retries == 2



# --- reanudar sin repetir trabajo ---


@responses.activate
def test_failed_sites_are_not_rescanned_by_default(db, wappalyzer):
    Site(url="ya_fallo.com", position=1, retries=1).save()
    Site(url="nuevo.com", position=2).save()
    responses.add(responses.GET, "https://nuevo.com", body=WP_HTML)

    result = scan_pending_sites(limit=10, wappalyzer=wappalyzer)

    assert result.processed == 1
    assert [c.request.url for c in responses.calls] == ["https://nuevo.com/"]
    assert Site.objects.get(url="ya_fallo.com").retries == 1


@responses.activate
def test_stop_then_resume_never_scans_a_site_twice(db, wappalyzer):
    for i in range(1, 9):
        Site(url=f"s{i}.com", position=i).save()
        responses.add(responses.GET, f"https://s{i}.com", body=WP_HTML)
    done = []

    first = scan_pending_sites(
        limit=100, wappalyzer=wappalyzer, workers=1, progress=lambda r: done.append(r.processed),
        should_stop=lambda: len(done) >= 3,
    )
    assert first.stopped is True
    assert 3 <= first.processed < 8
    assert Site.objects(finished=True).count() == first.processed  # lo hecho queda guardado

    second = scan_pending_sites(limit=100, wappalyzer=wappalyzer, workers=1)

    assert second.stopped is False
    assert first.processed + second.processed == 8
    urls = [c.request.url for c in responses.calls]
    assert len(urls) == len(set(urls)) == 8  # ninguna URL se pidió dos veces
    assert Site.objects(finished=True).count() == 8


@responses.activate
def test_stop_with_parallel_workers_keeps_finished_results(db, wappalyzer):
    for i in range(1, 41):
        Site(url=f"p{i}.com", position=i).save()
        responses.add(responses.GET, f"https://p{i}.com", body=WP_HTML)
    seen = []

    result = scan_pending_sites(
        limit=100, wappalyzer=wappalyzer, workers=4, progress=lambda r: seen.append(1),
        should_stop=lambda: len(seen) >= 5,
    )

    assert result.stopped is True
    assert 5 <= result.processed < 40
    assert Site.objects(finished=True).count() == result.processed


@responses.activate
def test_scan_pages_through_pending_sites_in_position_order(db, wappalyzer):
    for i in range(1, 8):
        Site(url=f"g{i}.com", position=i).save()
        responses.add(responses.GET, f"https://g{i}.com", body=WP_HTML)

    result = scan_pending_sites(limit=100, wappalyzer=wappalyzer, workers=1, page_size=2)

    assert result.processed == 7
    assert [c.request.url for c in responses.calls] == [f"https://g{i}.com/" for i in range(1, 8)]


@responses.activate
def test_limit_is_respected_across_pages(db, wappalyzer):
    for i in range(1, 8):
        Site(url=f"l{i}.com", position=i).save()
        responses.add(responses.GET, f"https://l{i}.com", body=WP_HTML)
    assert scan_pending_sites(limit=5, wappalyzer=wappalyzer, page_size=2).processed == 5
    assert Site.objects(finished=True).count() == 5


@responses.activate
def test_retry_failed_pages_without_looping_forever(db, wappalyzer):
    """Con retry_failed los fallidos siguen pendientes: la paginación por posición evita bucles."""
    for i in range(1, 6):
        Site(url=f"f{i}.com", position=i).save()
        for url in (f"https://f{i}.com", f"http://f{i}.com", f"https://www.f{i}.com"):
            responses.add(responses.GET, url, body=ConnectionError("down"))
    result = scan_pending_sites(limit=100, wappalyzer=wappalyzer, retry_failed=True, page_size=2, max_retries=10)
    assert (result.processed, result.failed) == (5, 5)
    assert all(s.retries == 1 for s in Site.objects)


@responses.activate
def test_detect_logs_the_error_class_of_each_failed_candidate(wappalyzer):
    import logging
    import requests

    for url in ("https://roto.com", "http://roto.com"):
        responses.add(responses.GET, url, body=requests.exceptions.ConnectTimeout("t"))
    responses.add(responses.GET, "https://www.roto.com", body=requests.exceptions.SSLError("s"))
    records = []
    handler = logging.Handler()
    handler.emit = records.append
    logger = logging.getLogger("webtechstats.detection")
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        assert detect_technologies("roto.com", wappalyzer) is None
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)

    messages = [r.getMessage() for r in records]
    assert sum("ConnectTimeout" in m for m in messages) == 2
    assert sum("SSLError" in m for m in messages) == 1
    assert all("roto.com" in m for m in messages)


# --- sitios descartados: marcados para no volver a escanearlos ---


def _all_fail(host, exc):
    for url in (f"https://{host}", f"http://{host}", f"https://www.{host}"):
        responses.add(responses.GET, url, body=exc)


@responses.activate
def test_failed_site_is_marked_discarded_with_reason(db, wappalyzer):
    import requests

    Site(url="muerto.com", position=1).save()
    _all_fail("muerto.com", requests.exceptions.ConnectTimeout("t"))

    scan_pending_sites(limit=10, wappalyzer=wappalyzer)

    site = Site.objects.get(url="muerto.com")
    assert site.discarded is True
    assert site.discard_reason == "ConnectTimeout"
    assert site.finished is False and site.retries == 1


@responses.activate
def test_discarded_sites_are_never_scanned_again_by_default(db, wappalyzer):
    Site(url="descartado.com", position=1, discarded=True, discard_reason="ConnectionError").save()
    Site(url="nuevo.com", position=2).save()
    responses.add(responses.GET, "https://nuevo.com", body=WP_HTML)

    assert scan_pending_sites(limit=10, wappalyzer=wappalyzer).processed == 1
    assert [c.request.url for c in responses.calls] == ["https://nuevo.com/"]


@responses.activate
def test_retry_failed_rescans_discarded_and_clears_the_mark_on_success(db, wappalyzer):
    Site(url="revivido.com", position=1, discarded=True, discard_reason="ConnectTimeout", retries=1).save()
    responses.add(responses.GET, "https://revivido.com", body=WP_HTML)

    result = scan_pending_sites(limit=10, wappalyzer=wappalyzer, retry_failed=True)

    assert result.ok == 1
    site = Site.objects.get(url="revivido.com")
    assert site.finished is True and site.discarded is False and site.discard_reason is None


@responses.activate
def test_retry_failed_keeps_the_mark_and_updates_reason_on_new_failure(db, wappalyzer):
    import requests

    Site(url="sigue.com", position=1, discarded=True, discard_reason="ConnectTimeout", retries=1).save()
    _all_fail("sigue.com", requests.exceptions.SSLError("s"))

    scan_pending_sites(limit=10, wappalyzer=wappalyzer, retry_failed=True)

    site = Site.objects.get(url="sigue.com")
    assert site.discarded is True and site.discard_reason == "SSLError" and site.retries == 2


@responses.activate
def test_site_that_responds_without_technologies_is_done_not_discarded(db, wappalyzer):
    Site(url="vacio.com", position=1).save()
    responses.add(responses.GET, "https://vacio.com", body="<html></html>")
    scan_pending_sites(limit=10, wappalyzer=wappalyzer)
    site = Site.objects.get(url="vacio.com")
    assert site.finished is True and site.discarded is False


# --- el pool nunca se desborda ---


@responses.activate
def test_scan_never_has_more_than_two_times_workers_in_flight(db, wappalyzer, monkeypatch):
    """Con un lote enorme no se encolan todos los sitios de golpe: la memoria no crece con el lote."""
    import time

    from webtechstats import detection

    for i in range(1, 121):
        Site(url=f"w{i}.com", position=i).save()
        responses.add(responses.GET, f"https://w{i}.com", body=WP_HTML)
    state = {"submitted": 0, "completed": 0, "max_in_flight": 0, "running": 0, "max_running": 0}

    class CountingPool(detection.ThreadPoolExecutor):
        def submit(self, fn, *args):
            state["submitted"] += 1
            state["max_in_flight"] = max(state["max_in_flight"], state["submitted"] - state["completed"])
            return super().submit(fn, *args)

    real_detect = detection._detect

    def slow_detect(url, wapp, timeout=10):
        state["running"] += 1
        state["max_running"] = max(state["max_running"], state["running"])
        time.sleep(0.002)
        state["running"] -= 1
        return real_detect(url, wapp, timeout)

    monkeypatch.setattr(detection, "ThreadPoolExecutor", CountingPool)
    monkeypatch.setattr(detection, "_detect", slow_detect)

    def progress(result):
        state["completed"] = result.processed

    result = scan_pending_sites(limit=1000, wappalyzer=wappalyzer, workers=4, progress=progress, page_size=10)

    assert result.processed == 120
    assert state["max_in_flight"] <= 8  # 2 × workers
    assert state["max_running"] <= 4


# --- reparto en trozos (varios procesos) ---


@responses.activate
def test_shards_are_disjoint_and_cover_every_pending_site(db, wappalyzer):
    for i in range(1, 13):
        Site(url=f"h{i}.com", position=i).save()
        responses.add(responses.GET, f"https://h{i}.com", body=WP_HTML)

    shards = []
    for shard in range(3):
        before = set(Site.objects(finished=True).scalar("url"))
        scan_pending_sites(limit=100, wappalyzer=wappalyzer, shard=(shard, 3), page_size=2)
        shards.append(set(Site.objects(finished=True).scalar("url")) - before)

    assert shards[0] == {f"h{i}.com" for i in (3, 6, 9, 12)}   # position % 3 == 0
    assert shards[1] == {f"h{i}.com" for i in (1, 4, 7, 10)}
    assert shards[2] == {f"h{i}.com" for i in (2, 5, 8, 11)}
    assert sum(len(s) for s in shards) == 12                   # disjuntos y completos
    urls = [c.request.url for c in responses.calls]
    assert len(urls) == len(set(urls)) == 12                   # nada se pidió dos veces


@responses.activate
def test_shard_respects_the_limit_and_resumes_where_it_left_off(db, wappalyzer):
    for i in range(1, 31):
        Site(url=f"r{i}.com", position=i).save()
        responses.add(responses.GET, f"https://r{i}.com", body=WP_HTML)
    first = scan_pending_sites(limit=4, wappalyzer=wappalyzer, shard=(1, 3), page_size=3)
    second = scan_pending_sites(limit=100, wappalyzer=wappalyzer, shard=(1, 3), page_size=3)
    assert first.processed == 4
    assert first.processed + second.processed == 10            # los 10 sitios con position % 3 == 1
    assert Site.objects(finished=True).count() == 10

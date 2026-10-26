# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
import json

import pytest
from requests.structures import CaseInsensitiveDict

from webtechstats.wappalyzer import Wappalyzer, WebPage

APPS = {
    "Nginx": {"cats": [22], "headers": {"Server": "nginx"}},
    "WordPress": {
        "cats": [1],
        "meta": {"generator": "WordPress"},
        "html": r"wp-content",
        "implies": ["PHP", "MySQL"],
    },
    "PHP": {"cats": [27], "headers": {"X-Powered-By": r"PHP/([\d.]+)\;version:\1"}},
    "MySQL": {"cats": [34]},
    "jQuery": {"cats": [59], "script": r"jquery[.-]([\d.]+)\.js"},
    "RegexRota": {"html": "(unclosed"},
}
CATEGORIES = {"1": "CMS", "22": "Web servers", "27": "Programming languages", "34": "Databases", "59": "JavaScript libraries"}


@pytest.fixture
def wappalyzer():
    return Wappalyzer(CATEGORIES, json.loads(json.dumps(APPS)))


def page(html="<html></html>", headers=None, url="https://example.org"):
    # requests entrega las cabeceras en un dict insensible a mayúsculas
    return WebPage(url, html, CaseInsensitiveDict(headers or {}))


def test_detects_by_header(wappalyzer):
    assert wappalyzer.analyze(page(headers={"Server": "nginx/1.25"})) == {"Nginx"}


def test_detects_by_script(wappalyzer):
    html = '<script src="/js/jquery-3.7.1.js"></script>'
    assert wappalyzer.analyze(page(html)) == {"jQuery"}


def test_meta_and_implies_are_transitive(wappalyzer):
    html = '<meta name="generator" content="WordPress 6.5">'
    assert wappalyzer.analyze(page(html)) == {"WordPress", "PHP", "MySQL"}


def test_detects_by_html(wappalyzer):
    assert "WordPress" in wappalyzer.analyze(page('<link href="/wp-content/x.css">'))


def test_no_match(wappalyzer):
    assert wappalyzer.analyze(page()) == set()


def test_invalid_regex_never_matches(wappalyzer):
    with pytest.warns(UserWarning):
        w = Wappalyzer(CATEGORIES, json.loads(json.dumps(APPS)))
    assert "RegexRota" not in w.analyze(page("(unclosed"))


def test_categories(wappalyzer):
    assert wappalyzer.get_categories("Nginx") == ["Web servers"]
    assert wappalyzer.analyze_with_categories(page(headers={"Server": "nginx"})) == {
        "Nginx": {"categories": ["Web servers"]}
    }


def test_webpage_requires_dict_like_headers():
    with pytest.raises(ValueError):
        WebPage("https://x", "<html></html>", None)


def test_latest_loads_bundled_rules():
    w = Wappalyzer.latest()
    assert len(w.apps) > 1000
    html = '<meta name="generator" content="WordPress 6.5">'
    assert "WordPress" in w.analyze(page(html))


# --- límites de descarga: tamaño y tiempo total por página ---

import responses


@responses.activate
def test_new_from_url_caps_the_body_size(monkeypatch):
    monkeypatch.setattr("webtechstats.wappalyzer.MAX_BYTES", 1000)
    responses.add(responses.GET, "https://grande.com", body="<html>" + "a" * 50000 + "</html>")
    page = WebPage.new_from_url("https://grande.com")
    assert 0 < len(page.html) <= 1000


@responses.activate
def test_new_from_url_stops_reading_after_the_time_budget(monkeypatch):
    ticks = iter(range(0, 10000, 100))  # cada lectura del reloj "pasa" 100 s
    monkeypatch.setattr("webtechstats.wappalyzer.time.monotonic", lambda: next(ticks))
    responses.add(responses.GET, "https://lento.com", body="<html>" + "a" * 50000 + "</html>")
    page = WebPage.new_from_url("https://lento.com")
    assert 0 < len(page.html) <= 8192  # solo el primer bloque


@responses.activate
def test_new_from_url_small_pages_are_read_completely():
    responses.add(responses.GET, "https://normal.com", body="<html><body>hola</body></html>")
    assert "hola" in WebPage.new_from_url("https://normal.com").html

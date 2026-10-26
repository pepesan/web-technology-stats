# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Generador de gráficas para el blog: datos desde reports/ y SVG + PNG en la carpeta del post (año/mes)."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import blog_charts as bc  # noqa: E402


def cut(tld, finished, items_by_topic, max_position=None):
    return {
        "report": "r", "max_position": max_position, "tld": tld,
        "summary": {"total": finished + 10, "finished": finished, "pending": 0, "failed": 10, "with_tech": finished, "distinct_tech": 3},
        "topics": [
            {"key": k, "label": k, "distinct": len(v), "categories": sorted({i["category"] for i in v}), "items": v}
            for k, v in items_by_topic.items()
        ],
    }


def item(tech, count, base, category="Programming languages"):
    return {"tech": tech, "count": count, "pct": round(100 * count / base, 1), "category": category}


@pytest.fixture
def reports(tmp_path):
    def write(rid, name, data):
        path = tmp_path / rid / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    for top, base, php, java in [(100, 80, 40, 8), (1000, 800, 300, 80), (None, 8000, 2000, 400)]:
        write("w", f"top-{top or 'all'}.json", cut(None, base, {"lang_back": [item("PHP", php, base), item("Java", java, base)],
              "other": [item("WordPress", 90, base, "CMS"), item("Nginx", 50, base, "Web servers")]}, top))
    write("w-es", "top-all.json", cut("es", 500, {"lang_back": [item("PHP", 300, 500)]}))
    (tmp_path / "index.json").write_text(json.dumps({"reports": [
        {"id": "w", "year": 2026, "scope": "all", "tops": [100, 1000], "total": 8010, "finished": 8000},
        {"id": "w-es", "year": 2026, "scope": "es", "tops": [], "total": 510, "finished": 500},
    ]}))
    return tmp_path


def test_spanish_number_formatting():
    assert bc.fmt_int(1234567) == "1.234.567"
    assert bc.fmt_pct(24.44) == "24,4 %"


def test_topic_items_filters_by_category(reports):
    data = bc.load_cut(reports, "w")
    assert [i["tech"] for i in bc.topic_items(data, "other")] == ["WordPress", "Nginx"]
    assert [i["tech"] for i in bc.topic_items(data, "other", category="CMS")] == ["WordPress"]
    assert bc.topic_items(data, "inexistente") == []


def test_evolution_follows_the_tech_across_cuts(reports):
    evo = bc.evolution(reports, "w", "lang_back", ["PHP", "Java", "Rust"])
    assert [label for label, _ in evo["PHP"]] == ["Top 100", "Top 1k", "Todos"]
    assert [pct for _, pct in evo["PHP"]] == [50.0, 37.5, 25.0]
    assert [pct for _, pct in evo["Rust"]] == [0.0, 0.0, 0.0]  # ausente = 0


def test_evolution_default_cuts_are_the_standard_ones_and_dedupe_the_million(tmp_path):
    index = {"reports": [
        {"id": "full", "tops": [100, 1000, 10000, 100000, 200000, 900000, 1000000]},
        {"id": "short", "tops": [100, 1000]},
    ]}
    (tmp_path / "index.json").write_text(json.dumps(index))
    assert bc.available_cuts(tmp_path, "full") == [100, 1000, 10000, 100000, 1000000]
    assert bc.available_cuts(tmp_path, "short") == [100, 1000, None]


def test_axis_percent_labels():
    assert [bc.fmt_axis_pct(v) for v in (100, 10, 1, 0.1, 0.01)] == ["100 %", "10 %", "1 %", "0,1 %", "0,01 %"]


def test_evolution_respects_the_requested_cuts(reports):
    evo = bc.evolution(reports, "w", "lang_back", ["PHP"], cuts=[1000, None])
    assert [label for label, _ in evo["PHP"]] == ["Top 1k", "Todos"]


def test_post_images_dir_follows_year_month_pattern(tmp_path):
    path = bc.post_images_dir(tmp_path, date(2026, 11, 9), "lenguajes-backend-2026")
    assert path == tmp_path / "src/content/blog/2026/11/2026-11-09-lenguajes-backend-2026/images"


@pytest.mark.parametrize("draw", ["bars", "evolution", "compare", "coverage", "values"])
def test_every_chart_writes_svg_and_png(reports, tmp_path, draw):
    world = bc.load_cut(reports, "w")
    es = bc.load_cut(reports, "w-es")
    out = tmp_path / "images" / "grafica"
    if draw == "bars":
        files = bc.draw_bars(bc.topic_items(world, "lang_back"), "Lenguajes", "n = 8.000", out)
    elif draw == "evolution":
        files = bc.draw_evolution(bc.evolution(reports, "w", "lang_back", ["PHP", "Java"]), "Evolución", "sub", out)
    elif draw == "compare":
        files = bc.draw_compare(bc.topic_items(world, "lang_back"), bc.topic_items(es, "lang_back"), "Mundo", "España", "Comparativa", "sub", out)
    elif draw == "values":
        files = bc.draw_values([("1×16", 269, "269 sitios/min"), ("10×8", 1779, "1.779 sitios/min")], "Ritmo", "sub", out)
    else:
        files = bc.draw_coverage(851742, 148258, "Cobertura", out)
    assert sorted(f.suffix for f in files) == [".png", ".svg"]
    assert files[0].parent == tmp_path / "images"
    png = next(f for f in files if f.suffix == ".png")
    svg = next(f for f in files if f.suffix == ".svg")
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and png.stat().st_size > 5000
    assert "<svg" in svg.read_text()[:600]


def test_series_is_a_well_formed_plan():
    import generate_blog_charts as gen

    slugs = [p.slug for p in gen.SERIES]
    dates = [p.date for p in gen.SERIES]
    assert len(slugs) == len(set(slugs)) == 10
    assert dates == sorted(dates) and dates[0] >= date(2026, 10, 26)
    assert all(slug and slug == slug.lower() and " " not in slug for slug in slugs)


REAL = Path(__file__).resolve().parent.parent / "reports" / "index.json"


@pytest.mark.skipif(not REAL.exists(), reason="requiere el informe real en reports/")
def test_series_generates_every_image_in_year_month_folders(tmp_path):
    import generate_blog_charts as gen

    written = gen.generate(tmp_path, REAL.parent, benchmark_csv=None, only={"lenguajes-backend-top-millon-2026"})
    files = [f for fs in written.values() for f in fs]
    assert files and all("/src/content/blog/2026/10/2026-10-26-" in f.as_posix() and "/images/" in f.as_posix() for f in files)
    assert {f.suffix for f in files} == {".svg", ".png"}


def test_post_writer_wraps_prose_but_keeps_markdown_structure():
    import blog_posts_lib as lib

    long = " ".join(["palabra"] * 40)
    prose = lib.wrap_markdown(long).split("\n")
    assert len(prose) > 2 and all(len(l) <= 80 for l in prose)

    bullet = lib.wrap_markdown(f"- {long}").split("\n")
    assert bullet[0].startswith("- palabra") and bullet[1].startswith("  palabra") and all(len(l) <= 80 for l in bullet)

    heading = f"## Título largo {long}"
    assert lib.wrap_markdown(heading).strip() == heading  # los títulos no se parten
    assert lib.wrap_markdown("![alt](images/x.png)").strip() == "![alt](images/x.png)"
    table = f"| a | b |\n|---|---|\n| {long} | 2 |"
    assert lib.wrap_markdown(table).strip() == table
    code = f"```bash\n{long}\n```"
    assert lib.wrap_markdown(code).strip() == code  # el bloque de código queda intacto
    assert lib.wrap_markdown("uno\ndos\n\ntres").split("\n")[:3] == ["uno dos", "", "tres"]  # une líneas de un párrafo


def test_frontmatter_follows_the_blog_convention():
    import blog_posts_lib as lib

    front = lib.frontmatter("Título", "Una descripción " * 12, date(2026, 11, 2), ["a", "b"], 5)
    assert front.startswith('---\ntitle: "Título"\nauthor: David Vaquero <aka pepesan>\ndescription: "Una')
    assert "\ndate: 2026-11-02\nlang: es\ntag: a, b\nduration: 5min\nvideo: false\ndraft: true\n---\n" in front
    block = front.split("\ndescription: ")[1].split("\ndate:")[0]
    lines = ("description: " + block).split("\n")
    assert all(len(l) <= 80 for l in lines) and lines[1].startswith("  ") and lines[-1].endswith('"')
    with pytest.raises(ValueError):
        lib.frontmatter('con "comillas"', "x", date(2026, 1, 1), [], 1)

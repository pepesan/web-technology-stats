#!/usr/bin/env python3
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Genera (SVG + PNG) las gráficas de la serie de entradas «Top 1M 2026» en la carpeta de cada post del blog.

Lee los informes estáticos de ./reports (sin MongoDB) y escribe en
<blog>/src/content/blog/AAAA/MM/AAAA-MM-DD-<slug>/images/.

Uso: ./scripts/generate_blog_charts.py [--blog ~/WebstormProjects/blogv2] [--reports reports] [--only SLUG ...]
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog_charts as bc  # noqa: E402

WORLD, SPAIN = "2026", "2026-es"
DEFAULT_BLOG = Path.home() / "WebstormProjects" / "blogv2"
BENCHMARK_CSV = "logs/benchmark_hilos_2026-10-25_20-52-17.csv"


@dataclass(frozen=True)
class Post:
    date: date
    slug: str
    title: str


SERIES = [
    Post(date(2026, 10, 26), "estudio-tecnologias-top-millon-tranco-2026", "Estudio 2026: qué tecnologías usa el millón de webs más visitadas"),
    Post(date(2026, 10, 26), "lenguajes-backend-top-millon-2026", "Lenguajes de backend en el millón de webs más visitadas (2026)"),
    Post(date(2026, 10, 26), "frameworks-frontend-top-millon-2026", "Frameworks y librerías de frontend en el top 1M (2026)"),
    Post(date(2026, 10, 26), "bases-de-datos-top-millon-2026", "Bases de datos en el millón de webs más visitadas (2026)"),
    Post(date(2026, 10, 26), "frameworks-backend-top-millon-2026", "Frameworks de backend en el top 1M (2026)"),
    Post(date(2026, 10, 26), "cms-wordpress-top-millon-2026", "WordPress y los CMS en el millón de webs más visitadas (2026)"),
    Post(date(2026, 10, 26), "servidores-web-cdn-top-millon-2026", "Servidores web y CDN en el top 1M (2026)"),
    Post(date(2026, 10, 26), "espana-dominios-es-top-millon-2026", "Las tecnologías de los dominios .es del top 1M (2026)"),
    Post(date(2026, 10, 26), "como-se-escanea-un-millon-de-webs", "Cómo escanear un millón de webs en menos de 7 horas"),
    Post(date(2026, 10, 26), "de-alexa-2020-a-tranco-2026-que-ha-cambiado", "De Alexa 2020 a Tranco 2026: qué ha cambiado"),
]

# Serie 2: los dominios .es del registro oficial de Red.es (listado RISP de 2026). Borradores; todas el mismo día.
SERIES_ES = [
    Post(date(2026, 10, 27), "registro-oficial-dominios-es-red-es-risp", "De dónde salen los dominios .es: el registro oficial de Red.es y el listado RISP"),
    Post(date(2026, 10, 27), "del-fichero-oficial-al-analisis-dominios-es", "Del fichero oficial al análisis: cómo estudiar 2,1 millones de dominios .es"),
    Post(date(2026, 10, 27), "cuantos-dominios-es-siguen-vivos-2020-2026", "Cuántos dominios .es siguen vivos: altas y bajas entre 2020 y 2026"),
    Post(date(2026, 10, 27), "lenguajes-y-servidores-dominios-es-2026", "Lenguajes, servidores y CDN de 2,1 millones de dominios .es (2026)"),
    Post(date(2026, 10, 27), "wordpress-cms-y-tiendas-dominios-es-2026", "WordPress, CMS y tiendas online en los dominios .es (2026)"),
    Post(date(2026, 10, 27), "frontend-y-bases-de-datos-dominios-es-2026", "Frontend, frameworks y bases de datos en los dominios .es (2026)"),
    Post(date(2026, 10, 27), "administracion-y-universidades-gob-es-edu-es-2026", "Administración y universidades: los dominios .gob.es y .edu.es"),
    Post(date(2026, 10, 27), "limites-etica-y-replicar-el-estudio-dominios-es", "Límites, ética y cómo replicar el estudio de los dominios .es"),
]
SUFFIXES = [("gob-es", ".gob.es"), ("edu-es", ".edu.es"), ("nom-es", ".nom.es"), ("org-es", ".org.es"), ("com-es", ".com.es")]


def _sub(cut: dict, scope: str = "Informe 2026") -> str:
    return f"{scope} · % de los {bc.fmt_int(cut['summary']['finished'])} sitios analizados que usan cada tecnología"


def generate(blog_root: Path, reports: Path, benchmark_csv: Path | None, only: set[str] | None = None) -> dict[str, list[Path]]:
    world = bc.load_cut(reports, WORLD)
    spain = bc.load_cut(reports, SPAIN)
    written: dict[str, list[Path]] = {}

    def out(post: Post, name: str) -> Path:
        return bc.post_images_dir(blog_root, post.date, post.slug) / name

    def add(post: Post, files: list[Path]) -> None:
        written.setdefault(post.slug, []).extend(files)

    def evo(topic, techs, category=None, cuts=None):
        return bc.evolution(reports, WORLD, topic, techs, category, cuts)

    def evo_title(what):  # subtítulo común de las gráficas de evolución
        return f"% de sitios analizados que usan {what} · cortes del ranking Tranco · escala logarítmica"

    for post in SERIES:
        if only and post.slug not in only:
            continue
        s = world["summary"]
        if post.slug.startswith("estudio-tecnologias"):
            add(post, bc.draw_coverage(s["finished"], s["failed"], "Resultado del escaneo del top 1M de Tranco", out(post, "cobertura-escaneo")))
            rows = [(t["label"], t["distinct"], bc.fmt_int(t["distinct"])) for t in world["topics"]]
            rows.sort(key=lambda r: -r[1])
            add(post, bc.draw_values(rows, "Tecnologías distintas detectadas por tema", f"{bc.fmt_int(s['distinct_tech'])} tecnologías en total · informe 2026", out(post, "tecnologias-por-tema")))
        elif post.slug.startswith("lenguajes-backend"):
            add(post, bc.draw_bars(bc.topic_items(world, "lang_back"), "Lenguajes de backend más detectados", _sub(world), out(post, "lenguajes-backend-top10"), n=10))
            add(post, bc.draw_evolution(evo("lang_back", ["PHP", "Java", "Node.js", "Python", "Ruby"]), "Lenguajes de backend según el corte del ranking", evo_title("cada lenguaje"), out(post, "lenguajes-backend-evolucion")))
        elif post.slug.startswith("frameworks-frontend"):
            add(post, bc.draw_bars(bc.topic_items(world, "front_libs"), "Frameworks y librerías de frontend más detectados", _sub(world), out(post, "frontend-top15"), n=15))
            add(post, bc.draw_evolution(evo("front_libs", ["Bootstrap", "jQuery", "React", "Vue.js", "Next.js"]), "Frontend según el corte del ranking", evo_title("cada librería"), out(post, "frontend-evolucion")))
        elif post.slug.startswith("bases-de-datos"):
            add(post, bc.draw_bars(bc.topic_items(world, "databases"), "Bases de datos más detectadas", _sub(world), out(post, "bases-de-datos-top10"), n=10))
            add(post, bc.draw_evolution(evo("databases", ["MySQL", "Redis", "MariaDB", "PostgreSQL"]), "Bases de datos según el corte del ranking", evo_title("cada base de datos"), out(post, "bases-de-datos-evolucion")))
        elif post.slug.startswith("frameworks-backend"):
            add(post, bc.draw_bars(bc.topic_items(world, "back_libs"), "Frameworks y librerías de backend más detectados", _sub(world), out(post, "backend-frameworks-top15"), n=15))
            add(post, bc.draw_evolution(evo("back_libs", ["Microsoft ASP.NET", "Express", "Ruby on Rails", "Laravel", "Django"]), "Frameworks de backend según el corte del ranking", evo_title("cada framework"), out(post, "backend-frameworks-evolucion")))
        elif post.slug.startswith("cms-wordpress"):
            add(post, bc.draw_bars(bc.topic_items(world, "other", "CMS"), "CMS más detectados", _sub(world), out(post, "cms-top12"), n=12))
            add(post, bc.draw_evolution(evo("other", ["WordPress", "Drupal", "Joomla", "TYPO3 CMS"], "CMS"), "CMS según el corte del ranking", evo_title("cada CMS"), out(post, "cms-evolucion")))
            add(post, bc.draw_bars(bc.topic_items(world, "other", "Ecommerce"), "Plataformas de comercio electrónico más detectadas", _sub(world), out(post, "ecommerce-top8"), n=8))
        elif post.slug.startswith("servidores-web"):
            add(post, bc.draw_bars(bc.topic_items(world, "other", "Web servers"), "Servidores web más detectados", _sub(world), out(post, "servidores-web-top8"), n=8))
            add(post, bc.draw_bars(bc.topic_items(world, "other", "CDN"), "CDN más detectadas", _sub(world), out(post, "cdn-top8"), n=8))
            add(post, bc.draw_evolution(evo("other", ["Cloudflare", "Nginx", "Apache HTTP Server", "LiteSpeed"]), "Cloudflare y los servidores web según el corte del ranking", evo_title("cada tecnología"), out(post, "servidores-evolucion")))
        elif post.slug.startswith("espana"):
            sub = f"% de sitios analizados · mundo ({bc.fmt_int(s['finished'])}) frente a España .es ({bc.fmt_int(spain['summary']['finished'])})"
            for name, topic, cat, title in [
                ("espana-lenguajes", "lang_back", None, "Lenguajes de backend: mundo y España"),
                ("espana-bases-de-datos", "databases", None, "Bases de datos: mundo y España"),
                ("espana-cms", "other", "CMS", "CMS: mundo y España"),
                ("espana-servidores", "other", "Web servers", "Servidores web: mundo y España"),
                ("espana-frontend", "front_libs", None, "Frontend: mundo y España"),
            ]:
                add(post, bc.draw_compare(bc.topic_items(world, topic, cat), bc.topic_items(spain, topic, cat), "Mundo", "España (.es)", title, sub, out(post, name), n=6))
            add(post, bc.draw_coverage(spain["summary"]["finished"], spain["summary"]["failed"], "Resultado del escaneo de los dominios .es", out(post, "espana-cobertura")))
        elif post.slug.startswith("como-se-escanea"):
            if benchmark_csv and Path(benchmark_csv).exists():
                with open(benchmark_csv, newline="") as fh:
                    rows = [(r["level"].replace("x", "×"), float(r["per_min_90"]), f"{bc.fmt_int(float(r['per_min_90']))} sitios/min · CPU máx. {r['cpu_max']} %") for r in csv.DictReader(fh)]
                add(post, bc.draw_values(rows, "Ritmo de escaneo según procesos × hilos", "primeros 1.000 sitios del top 1M · 10 núcleos · ritmo hasta el 90 % de sitios", out(post, "benchmark-procesos-hilos")))
        elif post.slug.startswith("de-alexa-2020"):
            rows = []
            for t in world["topics"]:
                items = [i for i in t["items"] if t["key"] not in ("other", "lang_front")]  # lang_front: solo XSLT/TypeScript residuales
                if items:
                    rows.append((t["label"], items[0]["pct"], f"{items[0]['tech']} · {bc.fmt_pct(items[0]['pct'])}"))
            cms = bc.topic_items(world, "other", "CMS")[0]
            rows.append(("CMS", cms["pct"], f"{cms['tech']} · {bc.fmt_pct(cms['pct'])}"))
            add(post, bc.draw_values(rows, "La tecnología líder de cada tema", _sub(world), out(post, "lideres-por-tema")))
    return written


def generate_es(blog_root: Path, reports: Path, reports_blog: Path, only: set[str] | None = None) -> dict[str, list[Path]]:
    """Gráficas de la serie de España: informes `2026` (Tranco) y `2026-es` (RISP 2026) de reports/, y los datos de
    reports-blog/ (solapes entre fuentes, motivos de fallo e informes por sufijo). Solo agregados: ningún dominio."""
    world, spain = bc.load_cut(reports, WORLD), bc.load_cut(reports, SPAIN)
    overlap = bc.parse_overlap((reports_blog / "solapes-fuentes.txt").read_text())
    reasons = bc.parse_failure_reasons((reports_blog / "resumen-risp2026.txt").read_text())
    suffix = {rid: bc.load_cut(reports_blog, rid) for rid, _ in SUFFIXES}
    s = spain["summary"]
    written: dict[str, list[Path]] = {}

    def total(source: str) -> int:
        return sum(count for sources, count, _ in overlap if source in sources)

    def both(a: str, b: str) -> int:
        return sum(count for sources, count, _ in overlap if a in sources and b in sources)

    def cmp(post: Post, name: str, topic: str, category: str | None, title: str, n: int) -> list[Path]:
        sub = f"% de sitios analizados · España ({bc.fmt_int(s['finished'])}) frente al mundo ({bc.fmt_int(world['summary']['finished'])})"
        return bc.draw_compare(bc.topic_items(spain, topic, category), bc.topic_items(world, topic, category),
                               "España (Red.es 2026)", "Mundo (Tranco)", title, sub, out(post, name), n=n)

    def out(post: Post, name: str) -> Path:
        return bc.post_images_dir(blog_root, post.date, post.slug) / name

    for post in SERIES_ES:
        if only and post.slug not in only:
            continue
        files: list[Path] = []
        if post.slug.startswith("registro-oficial"):
            rows = [(label, total(src), bc.fmt_int(total(src))) for label, src in
                    [("RISP 2026 (Red.es)", "risp2026"), ("RISP 2020 (Red.es)", "risp2020"), ("Common Crawl (.es)", "cc")]]
            files += bc.draw_values(rows, "Dominios .es según cada listado", "dominios únicos de cada fuente en el lote de estudio", out(post, "dominios-por-fuente"))
        elif post.slug.startswith("del-fichero"):
            files += bc.draw_coverage(s["finished"], s["failed"], "Resultado del escaneo del listado oficial de Red.es (2026)", out(post, "cobertura-risp2026"))
            base = total("risp2026")
            rows = [(label, 100 * both("risp2026", src) / base, f"{bc.fmt_int(both('risp2026', src))} · {bc.fmt_pct(100 * both('risp2026', src) / base)}")
                    for label, src in [("También en el RISP de 2020", "risp2020"), ("También en Common Crawl", "cc"), ("También en el top 1M de Tranco", "tranco")]]
            files += bc.draw_values(rows, "Qué parte del registro oficial aparece en otras fuentes", f"% de los {bc.fmt_int(base)} dominios del RISP 2026", out(post, "risp2026-en-otras-fuentes"))
        elif post.slug.startswith("cuantos-dominios"):
            groups = bc.cohorts(overlap, "risp2026", "risp2020")
            order = [("Permanentes (en 2020 y 2026)", "permanentes"), ("Altas (solo en 2026)", "altas"), ("Bajas (solo en 2020)", "bajas")]
            files += bc.draw_values([(label, groups[k][0], bc.fmt_int(groups[k][0])) for label, k in order],
                                    "Dominios del registro oficial entre 2020 y 2026", "listados RISP de enero de 2020 y de octubre de 2026", out(post, "altas-bajas"))
            files += bc.draw_values([(label, 100 * groups[k][1] / groups[k][0], f"{bc.fmt_pct(100 * groups[k][1] / groups[k][0])} · {bc.fmt_int(groups[k][1])} de {bc.fmt_int(groups[k][0])}") for label, k in order],
                                    "Qué parte de cada grupo respondió al escaneo", "% de dominios analizados con éxito (escaneo de octubre de 2026)", out(post, "respuesta-por-grupo"))
            rows = [(name, count, f"{bc.fmt_int(count)} · {bc.fmt_pct(100 * count / s['failed'])}") for name, count in reasons[:5]]
            files += bc.draw_values(rows, "Por qué no respondieron los dominios del RISP 2026", f"{bc.fmt_int(s['failed'])} sitios sin respuesta · clase de error de la petición HTTP", out(post, "motivos-fallo"))
        elif post.slug.startswith("lenguajes-y-servidores"):
            files += cmp(post, "es-lenguajes", "lang_back", None, "Lenguajes de backend: España y mundo", 6)
            files += cmp(post, "es-servidores", "other", "Web servers", "Servidores web: España y mundo", 6)
            files += cmp(post, "es-cdn", "other", "CDN", "CDN: España y mundo", 5)
            files += cmp(post, "es-paneles", "other", "Hosting panels", "Paneles de hosting: España y mundo", 3)
        elif post.slug.startswith("wordpress-cms"):
            files += cmp(post, "es-cms", "other", "CMS", "CMS: España y mundo", 7)
            files += cmp(post, "es-ecommerce", "other", "Ecommerce", "Tiendas online: España y mundo", 6)
            files += cmp(post, "es-page-builders", "other", "Page builders", "Constructores de páginas: España y mundo", 4)
        elif post.slug.startswith("frontend-y-bases"):
            files += cmp(post, "es-frontend", "front_libs", None, "Frameworks y librerías de frontend: España y mundo", 8)
            files += cmp(post, "es-bases-de-datos", "databases", None, "Bases de datos: España y mundo", 6)
            files += cmp(post, "es-frameworks-backend", "back_libs", None, "Frameworks de backend: España y mundo", 6)
        elif post.slug.startswith("administracion"):
            counts = sorted(((label, suffix[rid]["summary"]) for rid, label in SUFFIXES), key=lambda r: -r[1]["total"])
            files += bc.draw_values([(label, sm["total"], bc.fmt_int(sm["total"])) for label, sm in counts],
                                    "Dominios del RISP 2026 por sufijo de segundo nivel", "además de los dominios .es directos (el resto del listado)", out(post, "sufijos-dominios"))
            rest_total = s["total"] - sum(sm["total"] for _, sm in counts)
            rest_finished = s["finished"] - sum(sm["finished"] for _, sm in counts)
            rates = [(label, 100 * sm["finished"] / sm["total"], sm) for label, sm in counts] + [(".es directo", 100 * rest_finished / rest_total, {"finished": rest_finished, "total": rest_total})]
            rates.sort(key=lambda r: -r[1])
            files += bc.draw_values([(label, pct, f"{bc.fmt_pct(pct)} · {bc.fmt_int(sm['finished'])} de {bc.fmt_int(sm['total'])}") for label, pct, sm in rates],
                                    "Qué parte de cada sufijo respondió al escaneo", "% de dominios analizados con éxito (escaneo de octubre de 2026)", out(post, "sufijos-respuesta"))
            gob, edu = suffix["gob-es"], suffix["edu-es"]
            files += bc.draw_bars(bc.topic_items(gob, "front_libs"), "Frontend en los dominios .gob.es", _sub(gob, "RISP 2026 · .gob.es"), out(post, "gob-es-frontend"), n=5)
            files += bc.draw_bars(bc.topic_items(gob, "other", "CMS"), "CMS en los dominios .gob.es", _sub(gob, "RISP 2026 · .gob.es"), out(post, "gob-es-cms"), n=5)
            files += bc.draw_bars(bc.topic_items(edu, "other", "CMS"), "CMS en los dominios .edu.es", _sub(edu, "RISP 2026 · .edu.es"), out(post, "edu-es-cms"), n=5)
        if files:  # la entrada de cierre (límites y ética) no lleva gráficas
            written[post.slug] = files
    return written


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Genera las gráficas de las series del blog (SVG + PNG).")
    parser.add_argument("--serie", choices=["tranco", "es"], default="tranco", help="tranco = top 1M de Tranco (serie 1); es = dominios .es de Red.es (serie 2)")
    parser.add_argument("--blog", type=Path, default=DEFAULT_BLOG, help="raíz del proyecto Astro del blog")
    parser.add_argument("--reports", type=Path, default=root / "reports")
    parser.add_argument("--reports-blog", type=Path, default=root / "reports-blog", help="datos extra de la serie de España (solapes, fallos, sufijos)")
    parser.add_argument("--benchmark", type=Path, default=root / BENCHMARK_CSV)
    parser.add_argument("--only", nargs="*", help="solo estos slugs")
    args = parser.parse_args()
    only = set(args.only) if args.only else None
    if args.serie == "es":
        written = generate_es(args.blog, args.reports, args.reports_blog, only)
    else:
        written = generate(args.blog, args.reports, args.benchmark, only)
    for slug, files in written.items():
        print(f"{slug}: {len(files)} ficheros")
    print(f"Total: {sum(len(f) for f in written.values())} ficheros en {args.blog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Gráficas para las entradas del blog (SVG + PNG) a partir de los informes estáticos de reports/.

Paleta categórica validada del skill de visualización (azul, naranja, aguamarina, amarillo, magenta, ...),
barras finas con extremo redondeado, etiquetas directas y ejes discretos. Texto en tinta, nunca en el color de la serie.
"""

import json
import math
from datetime import date
from pathlib import Path

import matplotlib
import matplotlib.ticker  # noqa: F401

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FIG_W, DPI = 9.0, 200

plt.rcParams.update({
    "svg.fonttype": "path",  # texto convertido a trazos: el SVG se ve igual en cualquier visor
    "font.family": "DejaVu Sans",
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
})


# ---------- formato y datos ----------

def fmt_int(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_pct(p: float, digits: int = 1) -> str:
    return f"{p:.{digits}f}".replace(".", ",") + " %"


def fmt_axis_pct(p: float) -> str:
    """Etiqueta de eje sin decimales sobrantes: 100 %, 10 %, 1 %, 0,1 %, 0,01 %."""
    text = f"{p:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} %"


def cut_label(top: int | None) -> str:
    if top is None:
        return "Todos"
    return f"Top {top // 1_000_000}M" if top >= 1_000_000 else f"Top {top // 1000}k" if top >= 1000 else f"Top {top}"


def load_cut(reports: Path, report_id: str, top: int | None = None) -> dict:
    return json.loads((Path(reports) / report_id / f"top-{top or 'all'}.json").read_text())


def topic_items(cut: dict, topic: str, category: str | None = None) -> list[dict]:
    for t in cut["topics"]:
        if t["key"] == topic:
            return [i for i in t["items"] if category is None or i["category"] == category]
    return []


STANDARD_CUTS = [100, 1_000, 10_000, 100_000, 1_000_000]


def available_cuts(reports: Path, report_id: str) -> list[int | None]:
    """Cortes de la gráfica de evolución: los estándar que existen y, si falta el 1M, «Todos»."""
    index = json.loads((Path(reports) / "index.json").read_text())["reports"]
    entry = next(r for r in index if r["id"] == report_id)
    cuts: list[int | None] = [t for t in STANDARD_CUTS if t in entry["tops"]]
    return cuts if 1_000_000 in cuts else [*cuts, None]


def evolution(reports: Path, report_id: str, topic: str, techs: list[str], category: str | None = None,
              cuts: list[int | None] | None = None) -> dict[str, list[tuple[str, float]]]:
    """% de sitios analizados que usan cada tecnología en cada corte del ranking (0 si no aparece)."""
    result: dict[str, list[tuple[str, float]]] = {t: [] for t in techs}
    for top in (available_cuts(reports, report_id) if cuts is None else cuts):
        pct = {i["tech"]: i["pct"] for i in topic_items(load_cut(reports, report_id, top), topic, category)}
        for tech in techs:
            result[tech].append((cut_label(top), pct.get(tech, 0.0)))
    return result


def post_images_dir(blog_root: Path, post_date: date, slug: str) -> Path:
    """<blog>/src/content/blog/AAAA/MM/AAAA-MM-DD-<slug>/images (patrón año y mes del blog)."""
    name = f"{post_date:%Y-%m-%d}-{slug}"
    return Path(blog_root) / "src/content/blog" / f"{post_date:%Y}" / f"{post_date:%m}" / name / "images"


# ---------- dibujo ----------

def _finish(fig, stem: Path) -> list[Path]:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ("svg", "png"):
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.25)
        files.append(path)
    plt.close(fig)
    return files


def _titles(fig, title: str, subtitle: str) -> None:
    """Título y subtítulo alineados al borde izquierdo de la figura, con separación fija en puntos sobre el área de datos."""
    ax = fig.axes[0]
    ax.annotate(title, xy=(0, 1), xycoords=("figure fraction", "axes fraction"), xytext=(18, 36), textcoords="offset points",
                fontsize=15, fontweight="bold", ha="left", va="bottom", annotation_clip=False)
    ax.annotate(subtitle, xy=(0, 1), xycoords=("figure fraction", "axes fraction"), xytext=(18, 14), textcoords="offset points",
                fontsize=9.5, color=INK_2, ha="left", va="bottom", annotation_clip=False)


def _clean(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)


def draw_bars(items: list[dict], title: str, subtitle: str, stem: Path, n: int = 15) -> list[Path]:
    """Barras horizontales del Top N con el recuento y el % de sitios analizados como etiqueta directa."""
    items = items[:n]
    fig, ax = plt.subplots(figsize=(FIG_W, 0.42 * len(items) + 1.3))
    ys = list(range(len(items)))[::-1]
    pcts = [i["pct"] for i in items]
    ax.barh(ys, pcts, height=0.58, color=SERIES[0], zorder=3)
    top = max(pcts) if pcts else 1
    for y, i in zip(ys, items):
        ax.text(i["pct"] + top * 0.012, y, f'{fmt_pct(i["pct"])} · {fmt_int(i["count"])}', va="center", fontsize=9.5, color=INK)
    ax.set_yticks(ys, [i["tech"] for i in items], fontsize=10.5, color=INK)
    ax.set_xlim(0, top * 1.28)
    ax.xaxis.set_visible(False)
    ax.grid(False)
    _clean(ax)
    ax.spines["bottom"].set_visible(False)
    _titles(fig, title, subtitle)
    return _finish(fig, stem)


def _end_labels(ax, x: float, ends: list[tuple[str, float]], gap_px: float = 15.0) -> None:
    """Etiquetas al final de cada línea, separadas un mínimo en vertical para que no se pisen."""
    fig = ax.figure
    fig.canvas.draw()
    to_px, to_data = ax.transData, ax.transData.inverted()
    placed: list[float] = []
    for tech, value in sorted(ends, key=lambda e: -e[1]):
        y = to_px.transform((x, value))[1]
        if placed and y > placed[-1] - gap_px:
            y = placed[-1] - gap_px
        placed.append(y)
        ax.annotate(f"{tech} {fmt_pct(value)}", (x, to_data.transform((0, y))[1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=9, color=INK)


def draw_evolution(series: dict[str, list[tuple[str, float]]], title: str, subtitle: str, stem: Path) -> list[Path]:
    """Líneas del % de uso por corte del ranking (escala logarítmica, con leyenda y etiquetas directas)."""
    fig, ax = plt.subplots(figsize=(FIG_W, 5.0))
    labels = [x for x, _ in next(iter(series.values()))]
    xs = list(range(len(labels)))
    ends: list[tuple[str, float]] = []
    for idx, (tech, pts) in enumerate(series.items()):
        vals = [v if v > 0 else math.nan for _, v in pts]
        color = SERIES[idx % len(SERIES)]
        ax.plot(xs, vals, color=color, lw=2, marker="o", ms=6, mec=SURFACE, mew=1.5, label=tech, zorder=3)
        if not math.isnan(vals[-1]):
            ends.append((tech, vals[-1]))
    ax.set_yscale("log")
    positives = [v for pts in series.values() for _, v in pts if v > 0]
    lo, hi = 10 ** math.floor(math.log10(min(positives) * 0.8)), 10 ** math.ceil(math.log10(max(positives)))
    hi = hi if hi > lo else lo * 10
    ticks = [lo * 10 ** k for k in range(int(round(math.log10(hi / lo))) + 1)]
    ax.set_ylim(lo, hi)
    ax.set_yticks(ticks, [fmt_axis_pct(t) for t in ticks])
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xticks(xs, labels)
    ax.set_xlim(-0.3, len(xs) - 1 + (0.9 if len(series) <= 4 else 0.3))
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    _clean(ax)
    if len(series) <= 4:
        _end_labels(ax, xs[-1], ends)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=min(len(series), 5), frameon=False, fontsize=9.5)
    _titles(fig, title, subtitle)
    return _finish(fig, stem)


def draw_compare(a_items: list[dict], b_items: list[dict], a_label: str, b_label: str, title: str, subtitle: str,
                 stem: Path, n: int = 8) -> list[Path]:
    """Barras agrupadas de dos ámbitos (p. ej. mundo y España) para las N tecnologías más usadas de A."""
    techs = [i["tech"] for i in a_items[:n]]
    a = {i["tech"]: i["pct"] for i in a_items}
    b = {i["tech"]: i["pct"] for i in b_items}
    fig, ax = plt.subplots(figsize=(FIG_W, 0.62 * len(techs) + 1.5))
    ys = list(range(len(techs)))[::-1]
    h = 0.34
    ax.barh([y + h / 2 for y in ys], [a.get(t, 0) for t in techs], height=h - 0.03, color=SERIES[0], label=a_label, zorder=3)
    ax.barh([y - h / 2 for y in ys], [b.get(t, 0) for t in techs], height=h - 0.03, color=SERIES[1], label=b_label, zorder=3)
    top = max([*a.values(), *b.values(), 1])
    for y, t in zip(ys, techs):
        ax.text(a.get(t, 0) + top * 0.012, y + h / 2, fmt_pct(a.get(t, 0)), va="center", fontsize=8.8, color=INK)
        ax.text(b.get(t, 0) + top * 0.012, y - h / 2, fmt_pct(b.get(t, 0)), va="center", fontsize=8.8, color=INK)
    ax.set_yticks(ys, techs, fontsize=10.5, color=INK)
    ax.set_xlim(0, top * 1.2)
    ax.xaxis.set_visible(False)
    _clean(ax)
    ax.spines["bottom"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    _titles(fig, title, subtitle)
    return _finish(fig, stem)


def draw_coverage(finished: int, failed: int, title: str, stem: Path, pending: int = 0) -> list[Path]:
    """Barra apilada única; la leyenda con cifras va bajo cada segmento (el último alineado a su borde derecho)."""
    parts = [("Analizados", finished, SERIES[0]), ("Sin respuesta", failed, SERIES[1]), ("Pendientes", pending, "#8c8b86")]
    parts = [p for p in parts if p[1] > 0]
    total = sum(v for _, v, _ in parts)
    fig, ax = plt.subplots(figsize=(FIG_W, 2.6))
    left = 0.0
    for idx, (name, value, color) in enumerate(parts):
        ax.barh([0], [value], left=left, height=0.5, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
        last = idx == len(parts) - 1 and idx > 0
        x, ha = (left + value, "right") if last else (left, "left")
        ax.text(x, -0.38, f"■ {name}", ha=ha, va="top", fontsize=10.5, fontweight="bold", color=INK)
        ax.text(x, -0.56, f"{fmt_int(value)} · {fmt_pct(100 * value / total)}", ha=ha, va="top", fontsize=10, color=INK_2)
        left += value
    ax.set_xlim(0, total)
    ax.set_ylim(-0.9, 0.4)
    ax.axis("off")
    _titles(fig, title, f"{fmt_int(total)} dominios · informe 2026")
    return _finish(fig, stem)


def draw_values(rows: list[tuple[str, float, str]], title: str, subtitle: str, stem: Path) -> list[Path]:
    """Barras horizontales de valores arbitrarios: (etiqueta, valor, texto que se muestra al final de la barra)."""
    fig, ax = plt.subplots(figsize=(FIG_W, 0.5 * len(rows) + 1.3))
    ys = list(range(len(rows)))[::-1]
    top = max(v for _, v, _ in rows) or 1
    ax.barh(ys, [v for _, v, _ in rows], height=0.58, color=SERIES[0], zorder=3)
    for y, (_, v, text) in zip(ys, rows):
        ax.text(v + top * 0.012, y, text, va="center", fontsize=9.5, color=INK)
    ax.set_yticks(ys, [label for label, _, _ in rows], fontsize=10.5, color=INK)
    ax.set_xlim(0, top * 1.3)
    ax.xaxis.set_visible(False)
    _clean(ax)
    ax.spines["bottom"].set_visible(False)
    _titles(fig, title, subtitle)
    return _finish(fig, stem)

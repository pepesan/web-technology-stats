# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Escritura de entradas del blog: frontmatter y ajuste de párrafos a ~80 columnas (convención del blog)."""

import re
import textwrap
from datetime import date
from pathlib import Path

WIDTH = 80
AUTHOR = "David Vaquero <aka pepesan>"


def yaml_description(text: str) -> str:
    """description entre comillas dobles, doblada a ~80 columnas con sangría de 2 espacios."""
    if '"' in text:
        raise ValueError("la descripción no puede llevar comillas dobles")
    lines = textwrap.wrap(text, WIDTH - 1, initial_indent='description: "', subsequent_indent="  ")  # deja sitio a la comilla final
    return "\n".join(lines) + '"'


def frontmatter(title: str, description: str, post_date: date, tags: list[str], duration: int, draft: bool = True) -> str:
    if '"' in title:
        raise ValueError("el título no puede llevar comillas dobles")
    parts = [
        "---",
        f'title: "{title}"',
        f"author: {AUTHOR}",
        yaml_description(description),
        f"date: {post_date:%Y-%m-%d}",
        "lang: es",
        f"tag: {', '.join(tags)}",
        f"duration: {duration}min",
        "video: false",
    ]
    if draft:
        parts.append("draft: true")
    parts.append("---")
    return "\n".join(parts) + "\n"


def wrap_markdown(body: str) -> str:
    """Ajusta a ~80 columnas los párrafos y las listas; respeta títulos, imágenes, tablas y bloques de código."""
    out: list[str] = []
    in_code = False
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            out.append(textwrap.fill(" ".join(s.strip() for s in paragraph), WIDTH, break_long_words=False, break_on_hyphens=False))
            paragraph.clear()

    for raw in body.strip("\n").split("\n"):
        line = raw.rstrip()
        if line.startswith("```"):
            flush()
            in_code = not in_code
            out.append(line)
        elif in_code:
            out.append(line)
        elif not line:
            flush()
            out.append("")
        elif line.startswith(("#", "|", "!", "<")):
            flush()
            out.append(line)
        elif re.match(r"^(\s*[-*]|\s*\d+\.)\s", line):
            flush()
            marker = re.match(r"^(\s*(?:[-*]|\d+\.)\s+)", line).group(1)
            out.append(textwrap.fill(line[len(marker):], WIDTH, initial_indent=marker, subsequent_indent=" " * len(marker),
                                     break_long_words=False, break_on_hyphens=False))
        elif line.startswith(">"):
            flush()
            out.append(textwrap.fill(line.lstrip("> "), WIDTH, initial_indent="> ", subsequent_indent="> ",
                                     break_long_words=False, break_on_hyphens=False))
        else:
            paragraph.append(line)
    flush()
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text) + "\n"


def write_post(blog_root: Path, post_date: date, slug: str, front: str, body: str) -> Path:
    folder = Path(blog_root) / "src/content/blog" / f"{post_date:%Y}" / f"{post_date:%m}" / f"{post_date:%Y-%m-%d}-{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "index.md"
    path.write_text(front + "\n" + wrap_markdown(body))
    return path

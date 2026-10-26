# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Todo el código propio lleva la cabecera de autoría."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AUTHOR = "David Vaquero <pepesan@gmail.com>"
CODE_SUFFIXES = {".py", ".sh", ".js", ".vue", ".css"}
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "logs", "data", "__pycache__", "reports"}
# Derivados de python-Wappalyzer: conservan su autoría original, no se rotulan como obra propia.
THIRD_PARTY = {"src/webtechstats/wappalyzer.py", "legacy/wappalyze.py"}


def code_files():
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts) or not path.is_file():
            continue
        if (path.suffix in CODE_SUFFIXES or path.name == "Dockerfile") and rel.as_posix() not in THIRD_PARTY:
            yield rel


@pytest.mark.parametrize("rel", sorted(code_files()), ids=str)
def test_file_declares_its_author(rel):
    head = "\n".join((ROOT / rel).read_text().splitlines()[:5])
    assert AUTHOR in head, f"{rel}: falta la cabecera de autoría"

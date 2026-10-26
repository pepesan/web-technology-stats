# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""scripts/descargar_dominios_es.sh: lista de dominios .es desde el grafo de dominios de Common Crawl.

Siempre en una copia aislada y con `curl` falso: nunca toca la red ni el repositorio real.
"""

import gzip
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Formato real: id <TAB> nombre invertido <TAB> nº de hosts; ordenado por nombre invertido.
VERTICES = "".join(f"{i}\t{name}\t1\n" for i, name in enumerate([
    "com.google", "de.spiegel", "es.com.empresa", "es.edu.uni", "es.elpais", "es.foo.bar", "es.gob.ministerio",
    "es.marca", "es.sub", "es.xn--espaa-rta", "et.gov", "fr.lemonde", "es.despues.deletra",
]))


@pytest.fixture
def box(tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "descargar_dominios_es.sh", repo / "scripts")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "curl.txt"
    calls.write_text("")
    payload = tmp_path / "vertices.txt.gz"
    payload.write_bytes(gzip.compress(VERTICES.encode()))

    def install_curl(releases=("cc-main-2026-apr-may-jun", "cc-main-2026-jan-feb-mar"), fail_download=False):
        curl = bin_dir / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            f'echo "$@" >> "{calls}"\n'
            'url="${@: -1}"; head=0; for a in "$@"; do case "$a" in -*I*) head=1;; esac; done\n'
            'if [ "$head" = 1 ]; then\n'
            + "".join(f'  case "$url" in */{r}/domain/*) exit 0;; esac\n' for r in releases)
            + "  exit 22\nfi\n"
            + ("exit 22\n" if fail_download else f'cat "{payload}"\n')
        )
        curl.chmod(0o755)

    install_curl()

    class Box:
        path = repo
        set_curl = staticmethod(install_curl)

        @staticmethod
        def run(*args, **env):
            full = {**os.environ, "DOMINIOS_ES_MINIMO": "1", "DOMINIOS_ES_HOY": "2026-10-26", **env}
            full["PATH"] = f"{bin_dir}:{full['PATH']}"
            return subprocess.run([str(repo / "scripts" / "descargar_dominios_es.sh"), *args], capture_output=True,
                                  text=True, env=full, cwd=repo)

        @staticmethod
        def curl():
            return calls.read_text().splitlines()

        @staticmethod
        def dest():
            return repo / "data" / "dominios" / "dominios-es.csv"

    return Box


def test_writes_only_registrable_es_domains_reversed_with_positions(box):
    result = box.run()
    assert result.returncode == 0, result.stderr
    assert box.dest().read_text().splitlines() == [
        "1,empresa.com.es", "2,uni.edu.es", "3,elpais.es", "4,ministerio.gob.es", "5,marca.es", "6,sub.es", "7,xn--espaa-rta.es",
    ]  # es.foo.bar no es registrable bajo .es; et.* y lo posterior se descartan; nada de otros TLD


def test_default_destination_is_an_ignored_folder(box):
    box.run()
    ignored = subprocess.run(["git", "check-ignore", "-q", "data/dominios/dominios-es.csv"], cwd=ROOT).returncode == 0
    assert ignored  # la lista descargada nunca se versiona
    assert box.dest().parent == box.path / "data" / "dominios"


def test_uses_the_newest_release_that_exists(box):
    box.run()
    downloads = [c for c in box.curl() if c.startswith("-fsL")]  # las sondas de existencia son -fsI
    assert len(downloads) == 1 and "cc-main-2026-apr-may-jun" in downloads[0]  # jul-aug-sep y oct-nov-dec de 2026 aún no existen


def test_release_can_be_forced(box):
    box.run(CC_RELEASE="cc-main-2026-jan-feb-mar")
    assert any("cc-main-2026-jan-feb-mar-domain-vertices" in c for c in box.curl())
    assert not any("apr-may-jun" in c for c in box.curl())


def test_destination_can_be_given_as_argument(box):
    target = box.path / "otra" / "lista.csv"
    assert box.run(str(target)).returncode == 0
    assert target.read_text().startswith("1,empresa.com.es")


def test_does_not_download_again_when_the_file_exists(box):
    box.dest().parent.mkdir(parents=True)
    box.dest().write_text("1,ya.es\n")
    result = box.run()
    assert result.returncode == 0 and "ya existe" in result.stdout
    assert box.curl() == [] and box.dest().read_text() == "1,ya.es\n"


def test_failed_download_leaves_no_file_and_exits_with_error(box):
    box.set_curl(fail_download=True)
    result = box.run()
    assert result.returncode != 0 and "dominios" in result.stderr.lower()
    assert not box.dest().exists() and not list(box.path.rglob("*.tmp*"))


def test_no_release_available_is_an_error(box):
    box.set_curl(releases=())
    result = box.run()
    assert result.returncode != 0 and "lanzamiento" in result.stderr.lower()
    assert not box.dest().exists()


def test_too_few_domains_is_rejected_as_an_invalid_download(box):
    result = box.run(DOMINIOS_ES_MINIMO="1000")
    assert result.returncode != 0 and "esperaba" in result.stderr.lower()
    assert not box.dest().exists()

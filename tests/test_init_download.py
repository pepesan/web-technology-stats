"""`00_init.sh` descarga top-1m.csv (Tranco) si no existe. Siempre en una copia aislada, con curl y docker falsos."""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CSV_CONTENT = "1,google.com\n2,example.org\n3,wordpress.org\n"


@pytest.fixture
def box(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(ROOT / "00_init.sh", repo / "00_init.sh")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_calls, curl_calls = tmp_path / "docker.txt", tmp_path / "curl.txt"
    docker_calls.write_text("")
    curl_calls.write_text("")

    docker = bin_dir / "docker"
    docker.write_text(f'#!/usr/bin/env bash\necho "$@" >> "{docker_calls}"\n'
                      'if [ "$1" = "inspect" ]; then echo healthy; fi\n')
    docker.chmod(0o755)

    good_zip = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip, "w") as z:
        z.writestr("top-1m.csv", CSV_CONTENT)
    html = tmp_path / "error.html"
    html.write_text("<html>503 Service Unavailable</html>")

    def install_curl(behaviour):
        """`behaviour`: 'ok' (zip válido), 'fail' (HTTP error), 'html' (200 con una página de error)."""
        curl = bin_dir / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            f'echo "$@" >> "{curl_calls}"\n'
            'out=""; while [ $# -gt 0 ]; do [ "$1" = "-o" ] && out="$2"; shift; done\n'
            + {"ok": f'cp "{good_zip}" "$out"\n', "fail": "exit 22\n", "html": f'cp "{html}" "$out"\n'}[behaviour]
        )
        curl.chmod(0o755)

    install_curl("ok")

    class Box:
        path = repo
        set_curl = staticmethod(install_curl)

        @staticmethod
        def run(**env):
            full_env = dict(os.environ, MONGO_DATA_DIR=str(tmp_path / "mongo"), **env)
            full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
            return subprocess.run([str(repo / "00_init.sh")], capture_output=True, text=True, env=full_env, cwd=repo)

        @staticmethod
        def curl():
            return curl_calls.read_text().splitlines()

        @staticmethod
        def docker():
            return docker_calls.read_text().splitlines()

    return Box


def test_downloads_top_1m_csv_when_it_is_missing(box):
    result = box.run()
    assert result.returncode == 0, result.stderr
    assert (box.path / "top-1m.csv").read_text() == CSV_CONTENT
    assert len(box.curl()) == 1 and "https://tranco-list.eu/top-1m.csv.zip" in box.curl()[0]
    assert not list(box.path.glob("*.zip")) and not list(box.path.glob("*.tmp*"))  # sin restos


def test_does_not_download_again_when_the_file_already_exists(box):
    (box.path / "top-1m.csv").write_text("1,ya.com\n")
    assert box.run().returncode == 0
    assert box.curl() == []
    assert (box.path / "top-1m.csv").read_text() == "1,ya.com\n"


def test_an_empty_file_counts_as_missing(box):
    (box.path / "top-1m.csv").write_text("")
    assert box.run().returncode == 0
    assert (box.path / "top-1m.csv").read_text() == CSV_CONTENT


def test_download_url_can_be_overridden(box):
    box.run(TRANCO_URL="https://ejemplo.test/lista.zip")
    assert "https://ejemplo.test/lista.zip" in box.curl()[0]


def test_http_failure_leaves_no_partial_file_and_exits_with_error(box):
    box.set_curl("fail")
    result = box.run()
    assert result.returncode != 0 and "top-1m.csv" in result.stderr
    assert not (box.path / "top-1m.csv").exists()


def test_an_error_page_instead_of_a_zip_is_rejected(box):
    box.set_curl("html")
    result = box.run()
    assert result.returncode != 0
    assert not (box.path / "top-1m.csv").exists()


def test_mongo_is_still_started_even_if_the_download_fails(box):
    box.set_curl("fail")
    box.run()
    assert any("compose up -d" in c for c in box.docker())


def test_the_csv_is_gitignored():
    result = subprocess.run(["git", "check-ignore", "-q", "top-1m.csv"], cwd=ROOT)
    assert result.returncode == 0

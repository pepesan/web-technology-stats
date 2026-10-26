# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Imagen Docker estática (pepesan/web-stats): nginx + frontend compilado + informes JSON, sin base de datos."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCKER = ROOT / "docker" / "static"
ENTRYPOINT = DOCKER / "40-wts-config.sh"


def test_dockerfile_builds_the_frontend_and_serves_it_with_pinned_nginx():
    text = (DOCKER / "Dockerfile").read_text()
    froms = re.findall(r"^FROM (\S+)", text, re.M)
    assert froms[0].startswith("node:") and froms[-1].startswith("nginxinc/nginx-unprivileged:")
    assert all(not f.endswith((":latest", ":alpine", ":lts")) for f in froms)  # versiones fijadas
    assert "npm run build" in text
    assert re.search(r"^COPY (--chown=\S+ )?reports /usr/share/nginx/html/reports", text, re.M)
    assert "40-wts-config.sh" in text and "docker-entrypoint.d" in text
    assert "HEALTHCHECK" in text


def test_dockerfile_does_not_install_the_python_stack_or_need_mongo():
    text = (DOCKER / "Dockerfile").read_text().lower()
    assert "python" not in text and "mongo" not in text and "uv " not in text


def test_nginx_conf_compresses_json_and_never_caches_config():
    conf = (DOCKER / "nginx.conf").read_text()
    assert "gzip on" in conf and "application/json" in conf
    assert re.search(r"location = /config\.json\s*{[^}]*no-store", conf)


def test_dockerignore_keeps_reports_and_excludes_secrets():
    ignore = (ROOT / ".dockerignore").read_text().split()
    assert "reports" not in ignore and "webtechstats.toml" in ignore and ".env" in ignore


def run_entrypoint(tmp_path, **env):
    html = tmp_path / "html"
    html.mkdir(exist_ok=True)
    full_env = {"PATH": os.environ["PATH"], "WTS_HTML_DIR": str(html), **env}
    subprocess.run(["sh", str(ENTRYPOINT)], check=True, env=full_env, capture_output=True)
    return (html / "config.json").read_text()


def test_entrypoint_defaults_to_static_reports(tmp_path):
    assert run_entrypoint(tmp_path) == '{"source":"reports"}\n'


@pytest.mark.parametrize("value, expected", [("reports", "reports"), ("api", "api"), ("rm -rf /", "reports"), ('x"}', "reports")])
def test_entrypoint_writes_only_known_sources(tmp_path, value, expected):
    assert run_entrypoint(tmp_path, WTS_SOURCE=value) == f'{{"source":"{expected}"}}\n'


def test_build_script_tags_image_and_only_pushes_when_asked(tmp_path):
    box = tmp_path / "box"
    (box / "bin").mkdir(parents=True)
    (box / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "build_static_image.sh", box / "scripts")
    (box / "reports").mkdir()
    (box / "reports" / "index.json").write_text("{}")
    log = box / "docker.log"
    fake = box / "bin" / "docker"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n')
    fake.chmod(0o755)
    env = {"PATH": f"{box / 'bin'}:{os.environ['PATH']}", "HOME": str(tmp_path)}

    subprocess.run(["bash", str(box / "scripts" / "build_static_image.sh"), "2026"], check=True, env=env, cwd=box, capture_output=True)
    calls = log.read_text().splitlines()
    assert any(c.startswith("build") and "pepesan/web-stats:2026" in c and "pepesan/web-stats:latest" in c for c in calls)
    assert not any(c.startswith("push") for c in calls)

    log.unlink()
    subprocess.run(["bash", str(box / "scripts" / "build_static_image.sh"), "2026", "--push"], check=True, env=env, cwd=box, capture_output=True)
    pushed = [c for c in log.read_text().splitlines() if c.startswith("push")]
    assert pushed == ["push pepesan/web-stats:2026", "push pepesan/web-stats:latest"]


def test_build_script_refuses_to_build_without_reports(tmp_path):
    box = tmp_path / "box"
    (box / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "build_static_image.sh", box / "scripts")
    done = subprocess.run(["bash", str(box / "scripts" / "build_static_image.sh")], cwd=box, capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert done.returncode != 0 and "reports" in done.stderr


def test_image_runs_as_non_root_on_an_unprivileged_port():
    text = (DOCKER / "Dockerfile").read_text()
    assert re.search(r"^USER (101|nginx)\s*$", text, re.M)  # Trivy DS-0002
    assert "EXPOSE 8080" in text and "127.0.0.1:8080/" in text
    assert re.search(r"listen\s+8080;", (DOCKER / "nginx.conf").read_text())


def test_config_json_is_prepared_writable_for_the_non_root_user():
    text = (DOCKER / "Dockerfile").read_text()
    assert "--chown=101:101" in text and "config.json" in text


def test_base_os_packages_are_upgraded_and_the_final_user_is_not_root():
    text = (DOCKER / "Dockerfile").read_text()
    assert "apk upgrade --no-cache" in text
    users = re.findall(r"^USER (\S+)", text, re.M)
    assert users[-1] in {"101", "nginx"}  # tras el upgrade (root) se vuelve al usuario sin privilegios

# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""scripts/: exportar informes y escanear con Trivy (se prueban copiados a un directorio temporal, con uv/trivy falsos)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
BASH = shutil.which("bash")


@pytest.fixture
def box(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "bin").mkdir()
    for name in ("export_report.sh", "scan_trivy.sh", "build_static_image.sh"):
        shutil.copy(SCRIPTS / name, tmp_path / "scripts")
    return tmp_path


def fake(box, name, body='echo "$@" >> "$FAKE_LOG"'):
    path = box / "bin" / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)


def run(box, script, *args, path=True, **env):
    full = {"PATH": str(box / "bin") if path == "only-bin" else f"{box / 'bin'}:{os.environ['PATH']}", "HOME": str(box),
            "FAKE_LOG": str(box / "calls.log"), **env}
    return subprocess.run([BASH, str(box / "scripts" / script), *args], cwd=box, env=full, capture_output=True, text=True)


def calls(box):
    log = box / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_all_scripts_are_executable_bash_with_strict_mode():
    for script in SCRIPTS.glob("*.sh"):
        text = script.read_text()
        assert text.startswith("#!/usr/bin/env bash") and "set -euo pipefail" in text, script.name
        assert os.access(script, os.X_OK), f"{script.name} no es ejecutable"


# ---------- export_report.sh ----------


def test_export_report_runs_the_exporter_with_the_given_arguments(box):
    fake(box, "uv")
    done = run(box, "export_report.sh", "1", "2026", "Tranco 2026", "2026")
    assert done.returncode == 0, done.stderr
    assert calls(box) == ["run --project dashboard wts-export-report --batch 1 --id 2026 --label Tranco 2026 --year 2026 --out reports"]


def test_export_report_defaults_label_and_year_to_the_id(box):
    fake(box, "uv")
    run(box, "export_report.sh", "3", "2027")
    assert calls(box) == ["run --project dashboard wts-export-report --batch 3 --id 2027 --out reports"]


def test_export_report_requires_batch_and_id(box):
    fake(box, "uv")
    done = run(box, "export_report.sh", "1")
    assert done.returncode != 0 and "Uso" in done.stderr and calls(box) == []


# ---------- scan_trivy.sh ----------


def test_trivy_fs_scans_vulns_secrets_misconfig_and_licenses_skipping_heavy_dirs(box):
    fake(box, "trivy")
    done = run(box, "scan_trivy.sh")
    assert done.returncode == 0, done.stderr
    (call,) = calls(box)
    assert call.startswith("fs ")
    assert "--scanners vuln,secret,misconfig,license" in call
    for skipped in (".venv", "node_modules", "logs", "data/mongodb", ".git"):
        assert skipped in call.split("--skip-dirs ")[1].split(" ")[0]
    assert "--exit-code" not in call  # informativo por defecto


def test_trivy_writes_a_dated_report_in_logs(box):
    fake(box, "trivy", 'echo "$@" >> "$FAKE_LOG"; echo informe')
    run(box, "scan_trivy.sh")
    reports = list((box / "logs").glob("trivy_fs_*.txt"))
    assert len(reports) == 1 and "informe" in reports[0].read_text()


def test_trivy_strict_mode_fails_on_findings(box):
    fake(box, "trivy")
    run(box, "scan_trivy.sh", STRICT="1")
    assert "--exit-code 1" in calls(box)[0] and "--severity HIGH,CRITICAL" in calls(box)[0]


def test_trivy_image_mode_defaults_to_the_published_image(box):
    fake(box, "trivy")
    run(box, "scan_trivy.sh", "--image")
    run(box, "scan_trivy.sh", "--image", "pepesan/web-stats:2026")
    first, second = calls(box)
    assert first.startswith("image ") and first.endswith("pepesan/web-stats:latest")
    assert "--scanners vuln,secret" in first and second.endswith("pepesan/web-stats:2026")


def test_trivy_missing_binary_gives_a_clear_error(box):
    (box / "bin" / "dirname").symlink_to(shutil.which("dirname"))  # PATH sin trivy: solo lo imprescindible
    done = run(box, "scan_trivy.sh", path="only-bin")
    assert done.returncode != 0 and "trivy" in done.stderr.lower()

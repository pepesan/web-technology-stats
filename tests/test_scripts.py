"""Los scripts .sh de carga: sintaxis y argumentos que pasan al CLI (con un `uv` falso)."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LOAD_SCRIPTS = {
    "40_get_data_top10.sh": 10,
    "41_get_data_top1k.sh": 1000,
    "42_get_data_top10k.sh": 10000,
    "43_get_data_top100k.sh": 100000,
    "50_get_data_top1M.sh": 1000000,
}
ALL_SCRIPTS = sorted(p.name for p in ROOT.glob("*.sh")) + ["dashboard/run.sh"]


@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_script_has_valid_syntax_and_is_executable(script):
    path = ROOT / script
    assert os.access(path, os.X_OK), f"{script} no es ejecutable"
    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.fixture
def fake_uv(tmp_path):
    """Un `uv` que solo anota los argumentos con que se le llama."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.txt"
    uv = bin_dir / "uv"
    uv.write_text(f'#!/usr/bin/env bash\necho "$@" >> "{calls}"\n')
    uv.chmod(0o755)

    def run(script, *args, **env):
        full_env = {k: v for k, v in os.environ.items() if k not in ("WORKERS", "RETRY_FAILED", "MAX_RETRIES")}
        full_env.update(env)
        full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
        calls.write_text("")
        result = subprocess.run([str(ROOT / script), *args], capture_output=True, text=True, env=full_env, cwd=ROOT)
        assert result.returncode == 0, result.stderr
        return calls.read_text().splitlines()

    return run


@pytest.mark.parametrize("script, limit", LOAD_SCRIPTS.items())
def test_load_script_runs_import_scan_stats_for_its_volume(fake_uv, script, limit):
    imp, scan, stats = fake_uv(script)
    assert f"import-sites --file ./top-1m.csv --batch 1 --limit {limit}" in imp
    assert scan.startswith(f"run webtechstats scan --limit {limit} --batch 1")
    assert stats == "run webtechstats stats --top 20 --batch 1"


@pytest.mark.parametrize("script", LOAD_SCRIPTS)
def test_load_script_without_env_defers_to_configuration(fake_uv, script):
    """Sin WORKERS/RETRY_FAILED/MAX_RETRIES no se fuerza nada: manda la configuración (y no falla con `set -u`)."""
    _, scan, _ = fake_uv(script)
    assert "--workers" not in scan and "--retry-failed" not in scan and "--max-retries" not in scan


@pytest.mark.parametrize("script", LOAD_SCRIPTS)
def test_load_script_env_overrides_reach_the_cli(fake_uv, script):
    _, scan, _ = fake_uv(script, WORKERS="7", RETRY_FAILED="1", MAX_RETRIES="5")
    assert "--workers 7" in scan and "--retry-failed" in scan and "--max-retries 5" in scan


def test_load_script_batch_and_csv_arguments_reach_every_step(fake_uv):
    imp, scan, stats = fake_uv("41_get_data_top1k.sh", "otro.csv", "3")
    assert "--file otro.csv" in imp and "--batch 3" in imp
    assert "--batch 3" in scan and "--batch 3" in stats

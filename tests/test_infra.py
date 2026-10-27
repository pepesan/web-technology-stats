# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Infraestructura: compose.yaml, scripts de ciclo de vida de MongoDB y ajustes del host (sysctl)."""

import os
import re
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
SYSCTL = ROOT / "host" / "90-webtechstats.conf"


# ---------- compose.yaml ----------


@pytest.fixture(scope="module")
def compose():
    return yaml.safe_load((ROOT / "compose.yaml").read_text())


def test_mongo_has_enough_file_descriptors_for_many_connections(compose):
    nofile = compose["services"]["mongodb"]["ulimits"]["nofile"]
    assert nofile["soft"] >= 64000 and nofile["hard"] >= 64000  # con 1024 solo admite ~400 conexiones


def test_mongo_cache_is_capped_instead_of_taking_half_the_host_ram(compose):
    command = compose["services"]["mongodb"]["command"]
    command = command if isinstance(command, str) else " ".join(command)
    assert "--wiredTigerCacheSizeGB" in command and "--auth" in command


def test_mongo_data_dir_is_configurable_with_a_safe_default(compose):
    volumes = compose["services"]["mongodb"]["volumes"]
    assert "${MONGO_DATA_DIR:-./data/mongodb}:/data/db" in volumes


def test_dashboard_still_waits_for_a_healthy_mongo(compose):
    assert compose["services"]["dashboard"]["depends_on"]["mongodb"]["condition"] == "service_healthy"


# ---------- scripts con MONGO_DATA_DIR (docker falso, SIEMPRE en una copia aislada) ----------
#
# Los scripts hacen `cd` a su propio directorio y `99_destroy.sh --purge-data` ejecuta `rm -rf` sobre los datos de
# MongoDB. Por eso se ejecutan SIEMPRE copiados a un directorio temporal: un script defectuoso nunca debe poder
# tocar el ./data/mongodb real (un test lo borró una vez al ejecutarse sobre el repositorio).


@pytest.fixture
def sandbox(tmp_path):
    """Copia aislada del repositorio (solo los scripts) con un `docker` falso que anota sus llamadas."""
    import shutil

    repo = tmp_path / "repo"
    repo.mkdir()
    for script in ("00_init.sh", "01_launch.sh", "99_destroy.sh"):
        shutil.copy(ROOT / script, repo / script)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "docker_calls.txt"
    docker = bin_dir / "docker"
    docker.write_text(
        '#!/usr/bin/env bash\n'
        f'echo "$@" >> "{calls}"\n'
        'if [ "$1" = "inspect" ]; then echo healthy; fi\n'
    )
    docker.chmod(0o755)
    calls.write_text("")

    class Sandbox:
        path = repo
        bin = bin_dir
        docker_calls = calls

        @staticmethod
        def run(script, *args, stdin="", **env):
            full_env = dict(os.environ, **env)
            full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
            calls.write_text("")
            result = subprocess.run([str(repo / script), *args], input=stdin, capture_output=True, text=True,
                                    env=full_env, cwd=repo)
            return result, calls.read_text().splitlines()

    return Sandbox


def test_init_creates_the_configured_data_dir(sandbox, tmp_path):
    data = tmp_path / "fuera_de_dropbox" / "mongodb"
    (sandbox.path / "top-1m.csv").write_text("1,google.com\n")  # ya descargado: no se llama a curl
    result, calls = sandbox.run("00_init.sh", MONGO_DATA_DIR=str(data))
    assert result.returncode == 0, result.stderr
    assert data.is_dir()
    assert "compose up -d" in calls[0]
    assert not (sandbox.path / "data").exists()  # no ensució el directorio por defecto


def test_launch_requires_the_configured_data_dir_and_names_it(sandbox, tmp_path):
    data = tmp_path / "no_existe"
    result, calls = sandbox.run("01_launch.sh", MONGO_DATA_DIR=str(data))
    assert result.returncode == 1 and str(data) in result.stderr and calls == []
    data.mkdir()
    result, calls = sandbox.run("01_launch.sh", MONGO_DATA_DIR=str(data))
    assert result.returncode == 0 and any("compose up -d" in c for c in calls)


# ---------- 01_launch.sh: carga del backup si existe y la base está vacía ----------


@pytest.fixture
def restore_box(sandbox, tmp_path):
    """`docker` falso que contesta al recuento de `mongosh` (FAKE_COUNT) y guarda lo que recibe `mongorestore`."""
    restored = tmp_path / "restored.bin"
    (sandbox.bin / "docker").write_text(
        '#!/usr/bin/env bash\n'
        f'echo "$@" >> "{sandbox.docker_calls}"\n'
        'case "$*" in\n'
        '  inspect*) echo healthy ;;\n'
        '  *mongosh*) echo "${FAKE_COUNT:-0}" ;;\n'
        f'  *mongorestore*) cat > "{restored}" ;;\n'
        'esac\n'
    )
    data = tmp_path / "mongodb"
    data.mkdir()
    backups = tmp_path / "backups"
    backups.mkdir()

    def make_backup(name, content, checksum=True, listed_as=None):
        """`listed_as`: ruta que escribe el .sha256 (el real, hecho con `sha256sum data/backups/<f>`, lleva la carpeta)."""
        import hashlib

        (backups / name).write_bytes(content)
        if checksum:
            (backups / f"{name}.sha256").write_text(f"{hashlib.sha256(content).hexdigest()}  {listed_as or name}\n")

    class Box:
        restored_file = restored
        make = staticmethod(make_backup)

        @staticmethod
        def launch(**env):
            return sandbox.run("01_launch.sh", MONGO_DATA_DIR=str(data), BACKUP_DIR=str(backups), **env)

    Box.data = data
    return Box


def test_launch_restores_the_newest_backup_when_the_database_is_empty(restore_box):
    restore_box.make("webstats_2026-10-26_10-00-00.archive.gz", b"viejo")
    restore_box.make("webstats_2026-10-27_08-09-22.archive.gz", b"nuevo")
    result, calls = restore_box.launch(FAKE_COUNT="0")
    assert result.returncode == 0, result.stderr
    assert restore_box.restored_file.read_bytes() == b"nuevo"
    # la restauración no borra nada: nunca --drop
    assert any("mongorestore" in c for c in calls) and not any("--drop" in c for c in calls)


def test_launch_accepts_a_sha256_file_that_lists_the_path_it_was_made_from(restore_box):
    # así lo genera el comando del PLAN: `sha256sum data/backups/<f> > <f>.sha256`, con la carpeta en el contenido
    restore_box.make("webstats_2026-10-27_08-09-22.archive.gz", b"nuevo", listed_as="data/backups/webstats_2026-10-27_08-09-22.archive.gz")
    result, _ = restore_box.launch(FAKE_COUNT="0")
    assert result.returncode == 0, result.stderr
    assert restore_box.restored_file.read_bytes() == b"nuevo"


def test_launch_keeps_existing_data_and_does_not_restore(restore_box):
    restore_box.make("webstats_2026-10-27_08-09-22.archive.gz", b"nuevo")
    result, calls = restore_box.launch(FAKE_COUNT="4011304")
    assert result.returncode == 0, result.stderr
    assert not any("mongorestore" in c for c in calls)
    assert not restore_box.restored_file.exists()


def test_launch_without_backups_behaves_as_before(restore_box):
    result, calls = restore_box.launch(FAKE_COUNT="0")
    assert result.returncode == 0, result.stderr
    assert not any("mongosh" in c or "mongorestore" in c for c in calls)


def test_launch_with_a_backup_starts_even_if_the_data_dir_was_lost(restore_box):
    restore_box.make("webstats_2026-10-27_08-09-22.archive.gz", b"nuevo")
    import shutil

    shutil.rmtree(restore_box.data)
    result, _ = restore_box.launch(FAKE_COUNT="0")
    assert result.returncode == 0, result.stderr
    assert restore_box.data.is_dir()  # lo crea el script (si no, docker lo crearía como root)
    assert restore_box.restored_file.read_bytes() == b"nuevo"


def test_launch_refuses_a_backup_whose_checksum_does_not_match(restore_box):
    restore_box.make("webstats_2026-10-27_08-09-22.archive.gz", b"nuevo")
    (restore_box.restored_file.parent / "backups" / "webstats_2026-10-27_08-09-22.archive.gz").write_bytes(b"corrupto")
    result, calls = restore_box.launch(FAKE_COUNT="0")
    assert result.returncode == 1 and "sha256" in result.stderr.lower()
    assert not any("mongorestore" in c for c in calls)


def test_skip_restore_ignores_the_backups(restore_box):
    restore_box.make("webstats_2026-10-27_08-09-22.archive.gz", b"nuevo")
    result, calls = restore_box.launch(FAKE_COUNT="0", SKIP_RESTORE="1")
    assert result.returncode == 0, result.stderr
    assert not any("mongosh" in c or "mongorestore" in c for c in calls)


def test_purge_removes_only_the_configured_data_dir(sandbox, tmp_path):
    data = tmp_path / "mongodb"
    data.mkdir()
    (data / "fichero").write_text("x")
    default = sandbox.path / "data" / "mongodb"  # el directorio por defecto de la copia
    default.mkdir(parents=True)
    (default / "intocable").write_text("datos")
    result, _ = sandbox.run("99_destroy.sh", "--purge-data", stdin="y\n", MONGO_DATA_DIR=str(data))
    assert result.returncode == 0, result.stderr
    assert not data.exists()
    assert (default / "intocable").read_text() == "datos"


def test_purge_without_the_flag_or_when_cancelled_keeps_the_data(sandbox, tmp_path):
    data = tmp_path / "mongodb"
    data.mkdir()
    (data / "fichero").write_text("x")
    sandbox.run("99_destroy.sh", "--purge-data", stdin="n\n", MONGO_DATA_DIR=str(data))
    assert (data / "fichero").exists()
    sandbox.run("99_destroy.sh", MONGO_DATA_DIR=str(data))
    assert (data / "fichero").exists()


def test_the_real_data_dir_is_never_touched_by_the_test_suite():
    """Red de seguridad: si alguien vuelve a ejecutar un script destructivo en el repo real, esto lo delata."""
    scripts = [ROOT / "99_destroy.sh"]
    for script in scripts:
        text = script.read_text()
        assert "rm -rf" in text and '"$DATA_DIR"' in text  # el borrado va siempre contra la variable, nunca literal
        assert "rm -rf ./data" not in text


# ---------- host/90-webtechstats.conf ----------


def parse_sysctl(text):
    active = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert re.fullmatch(r"[a-z0-9_.]+ = .+", line), f"línea no válida: {line!r}"
        key, value = line.split(" = ", 1)
        active[key] = value
    return active


def test_sysctl_file_is_well_formed_and_keys_exist_on_this_kernel():
    active = parse_sysctl(SYSCTL.read_text())
    assert active, "el fichero no define ningún parámetro"
    for key in active:
        proc = Path("/proc/sys") / key.replace(".", "/")
        if key.startswith("net.netfilter."):
            continue  # solo existe con el módulo nf_conntrack cargado
        assert proc.exists(), f"{key} no existe en este kernel"


def test_sysctl_widens_ephemeral_ports_without_stealing_service_ports():
    active = parse_sysctl(SYSCTL.read_text())
    low, high = map(int, active["net.ipv4.ip_local_port_range"].split())
    assert low >= 20000 and high <= 65535 and high - low > 28232  # más puertos que el rango por defecto
    reserved = {int(p) for p in active["net.ipv4.ip_local_reserved_ports"].split(",")}
    assert 27017 in reserved  # MongoDB cae dentro del rango efímero: debe quedar reservado


def test_sysctl_does_not_change_host_wide_memory_policy_by_default():
    assert "vm.swappiness" not in parse_sysctl(SYSCTL.read_text())  # solo como opción comentada


def test_sysctl_values_are_sane():
    active = parse_sysctl(SYSCTL.read_text())
    assert active["net.ipv4.tcp_tw_reuse"] in {"0", "1", "2"}
    assert int(active["net.ipv4.tcp_fin_timeout"]) >= 15
    assert int(active["net.netfilter.nf_conntrack_max"]) >= 262144


# ---------- host/aplicar_sysctl.sh ----------


def run_apply(*args):
    return subprocess.run([str(ROOT / "host" / "aplicar_sysctl.sh"), *args], capture_output=True, text=True)


def test_apply_script_is_executable_with_valid_syntax():
    path = ROOT / "host" / "aplicar_sysctl.sh"
    assert os.access(path, os.X_OK)
    assert subprocess.run(["bash", "-n", str(path)], capture_output=True).returncode == 0


def test_dry_run_changes_nothing_needs_no_root_and_shows_current_and_proposed():
    result = run_apply("--dry-run")
    assert result.returncode == 0, result.stderr
    assert "net.ipv4.ip_local_port_range" in result.stdout and "20000" in result.stdout
    assert "no se ha modificado nada" in result.stdout.lower()


@pytest.mark.skipif(os.geteuid() == 0, reason="solo se puede comprobar sin ser root")
def test_apply_requires_root_and_touches_nothing_without_it():
    result = run_apply()
    assert result.returncode != 0 and "sudo" in result.stderr
    assert not Path("/etc/sysctl.d/90-webtechstats.conf").exists()


def test_dashboard_port_binds_to_localhost_unless_overridden(compose):
    # Sin autenticación: por defecto solo localhost; DASHBOARD_BIND permite abrirlo a la LAN.
    assert compose["services"]["dashboard"]["ports"] == ["${DASHBOARD_BIND:-127.0.0.1}:${DASHBOARD_PORT:-8000}:8000"]

"""CLI de web-technology-stats.

Ver CLI.md para la documentación detallada de cada comando.
"""

import logging
import os
import signal
import sys
import threading

import click

from . import __version__
from .config import LOG_LEVELS, ConfigError, LogConfig, MongoConfig, ScanConfig
from .db import close_db, init_db, ping
from .importer import import_sites
from .locks import ScanAlreadyRunning, scan_lock
from .logs import log_filename, setup_logging
from .parallel import ShardFailed, kill_children, run_sharded
from .detection import scan_pending_sites
from .stats import summary, top_technologies
from .wappalyzer import Wappalyzer


logger = logging.getLogger("webtechstats.cli")


def _connect() -> None:
    ctx = click.get_current_context()
    try:
        config = MongoConfig.load((ctx.obj or {}).get("config"))
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    init_db(config)


@click.group()
@click.version_option(version=__version__, prog_name="webtechstats")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Fichero TOML con la conexión a MongoDB (por defecto: ./webtechstats.toml o ~/.config/webtechstats/config.toml).",
)
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS, case_sensitive=False),
    default=None,
    help="Nivel del log a fichero (por defecto [log] level, INFO). El log va a logs/webtechstats.log.",
)
@click.pass_context
def main(ctx: click.Context, config_path: str | None, log_level: str | None) -> None:
    """Herramienta de detección de tecnologías web sobre listados masivos de dominios."""
    ctx.obj = {"config": config_path, "log_level": log_level}


def _start_log(command: str, batch: int | None = None) -> str:
    """Abre el log de esta ejecución: `<logs>/webtechstats_<comando>_batch-<N|all>_<fecha>.log`."""
    obj = click.get_current_context().obj or {}
    try:
        log_config = LogConfig.load(obj.get("config"))
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    log_file = setup_logging(log_config.dir, obj.get("log_level") or log_config.level, log_filename(command, batch))
    logger.info("Comando %s (log: %s)", command, log_file)
    return log_config.dir


@main.command("init-db")
def init_db_cmd() -> None:
    """Comprueba la conexión a MongoDB y crea los índices del modelo `Site`."""
    _start_log("init-db")
    _connect()
    if not ping():
        click.echo("No se pudo conectar a MongoDB con la configuración actual.", err=True)
        sys.exit(1)
    from .models import Site

    Site.ensure_schema()
    click.echo("Conexión OK e índices asegurados.")
    close_db()


@main.command("import-sites")
@click.option("--file", "csv_file", required=True, type=click.Path(exists=True), help="CSV posicion,dominio (formato Tranco).")
@click.option("--limit", type=int, default=None, help="Número máximo de filas a importar (por defecto: todas).")
@click.option("--batch", type=int, default=1, help="Identificador de lote asignado a los sitios importados.")
def import_sites_cmd(csv_file: str, limit: int | None, batch: int) -> None:
    """Importa un listado de dominios (p.ej. top-1m.csv) a la colección `Site`."""
    _start_log("import-sites", batch)
    _connect()
    from .models import Site

    Site.ensure_schema()
    result = import_sites(csv_file, limit=limit, batch=batch)
    summary_line = (
        f"Leídos: {result.read} | Importados: {result.imported} | "
        f"Ya existentes (omitidos): {result.skipped_existing}"
    )
    click.echo(summary_line)
    logger.info("import-sites lote %s: %s", batch, summary_line)
    close_db()


@main.command("scan")
@click.option("--limit", type=int, default=100, show_default=True, help="Número máximo de sitios pendientes a escanear.")
@click.option("--batch", type=int, default=None, help="Escanear solo los sitios de este lote (por defecto: todos los lotes).")
@click.option(
    "--workers",
    type=click.IntRange(min=1),
    default=None,
    help="Peticiones HTTP en paralelo. Por defecto el valor de [scan] workers de la configuración (4 si no se define).",
)
@click.option(
    "--processes",
    type=click.IntRange(min=1),
    default=None,
    help="Procesos en paralelo, cada uno con --workers hilos y un trozo disjunto de los sitios (usa varios núcleos; "
    "los hilos de un solo proceso comparten el GIL). Por defecto [scan] processes (1).",
)
@click.option(
    "--retry-failed",
    is_flag=True,
    help="Reintenta también los sitios que ya fallaron en este lote (por defecto no se vuelven a escanear).",
)
@click.option(
    "--max-retries",
    type=click.IntRange(min=1),
    default=None,
    help="Con --retry-failed: los sitios que ya han fallado tantas veces no se reintentan. Por defecto [scan] max_retries (10).",
)
def scan_cmd(
    limit: int,
    batch: int | None,
    workers: int | None,
    processes: int | None,
    max_retries: int | None,
    retry_failed: bool,
) -> None:
    """Escanea sitios pendientes (finished=False) y detecta sus tecnologías."""
    lock_dir = _start_log("scan", batch)
    try:  # un solo escaneo por lote a la vez; se libera al terminar el comando (o si el proceso muere)
        click.get_current_context().with_resource(scan_lock(lock_dir, batch))
    except ScanAlreadyRunning as exc:
        logger.error("%s", exc)
        raise click.ClickException(str(exc)) from exc
    ctx = click.get_current_context()
    if workers is None or max_retries is None or processes is None:  # los parámetros de CLI mandan sobre la configuración
        try:
            scan_config = ScanConfig.load((ctx.obj or {}).get("config"))
        except ConfigError as exc:
            raise click.ClickException(str(exc)) from exc
        workers = scan_config.workers if workers is None else workers
        max_retries = scan_config.max_retries if max_retries is None else max_retries
        processes = scan_config.processes if processes is None else processes
    _connect()
    from .models import Site

    Site.ensure_schema()
    wappalyzer = Wappalyzer.latest() if processes == 1 else None  # con varios procesos lo carga cada hijo
    start_line = (
        f"Escaneando con {processes} proceso(s) × {workers} hilo(s) = {processes * workers} peticiones simultáneas; "
        f"se omiten sitios con {max_retries} fallos o más."
    ) if processes > 1 else (
        f"Escaneando con {workers} hilo(s) simultáneo(s); se omiten sitios con {max_retries} fallos o más."
    )
    click.echo(start_line, err=True)
    logger.info("scan lote %s, límite %s: %s", batch, limit, start_line)

    def report(partial) -> None:
        if partial.processed % 100 == 0:
            line = f"… {partial.processed} procesados (OK: {partial.ok}, fallidos: {partial.failed})"
            click.echo(f"  {line}", err=True)
            logger.info("scan lote %s: %s", batch, line)

    # Parada ordenada: la primera señal deja de lanzar trabajo y guarda lo que está en vuelo; la segunda aborta.
    stop = threading.Event()
    previous = {}

    def request_stop(signum, _frame) -> None:
        if stop.is_set():
            logger.error("Segunda señal (%s): abortando sin esperar a las peticiones en vuelo", signum)
            click.echo("Abortando sin esperar a las peticiones en vuelo.", err=True)
            kill_children()
            os._exit(130)  # los resultados ya terminados están guardados; lo demás sigue pendiente
        stop.set()
        click.echo("Señal recibida: terminando los sitios en curso y saliendo (repite la señal para abortar ya)…", err=True)
        logger.warning("Parada solicitada (señal %s)", signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, request_stop)
    failure = None
    try:
        if processes > 1:
            obj = ctx.obj or {}
            log_config = LogConfig.load(obj.get("config"))
            try:
                result = run_sharded(
                    processes,
                    {
                        "limit": limit,
                        "batch": batch,
                        "workers": workers,
                        "max_retries": max_retries,
                        "retry_failed": retry_failed,
                        "config_path": obj.get("config"),
                        "log_dir": log_config.dir,
                        "log_level": obj.get("log_level") or log_config.level,
                    },
                    stop_event=stop,
                )
            except ShardFailed as exc:
                result, failure = exc.partial, str(exc)
        else:
            result = scan_pending_sites(
                limit=limit,
                wappalyzer=wappalyzer,
                batch=batch,
                workers=workers,
                progress=report,
                max_retries=max_retries,
                retry_failed=retry_failed,
                should_stop=stop.is_set,
            )
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    summary_line = f"Procesados: {result.processed} | OK: {result.ok} | Fallidos: {result.failed}"
    click.echo(summary_line)
    logger.info("scan lote %s: %s", batch, summary_line)
    if result.stopped:
        stopped_line = "Interrumpido: los resultados están guardados; relanza el mismo comando para continuar."
        click.echo(stopped_line)
        logger.warning("scan lote %s: %s", batch, stopped_line)
    close_db()
    if failure:
        logger.error("scan lote %s: %s", batch, failure)
        click.echo(f"Error: {failure}. Lo guardado se conserva; relanza el comando para continuar.", err=True)
        sys.exit(1)


@main.command("stats")
@click.option("--top", type=int, default=20, show_default=True, help="Número de tecnologías más frecuentes a mostrar.")
@click.option("--batch", type=int, default=None, help="Estadísticas solo de este lote (por defecto: todos los lotes).")
def stats_cmd(top: int, batch: int | None) -> None:
    """Muestra totales de sitios y el ranking de tecnologías más detectadas."""
    _start_log("stats", batch)
    _connect()
    data = summary(batch=batch)
    click.echo("Resumen:")
    click.echo(f"  Total:              {data['total']}")
    click.echo(f"  Finalizados:        {data['finished']}")
    click.echo(f"  Sin respuesta:      {data['failed']}")
    click.echo(f"  Pendientes:         {data['pending']}")
    click.echo(f"  Con tecnología:     {data['finished_with_tech']}")

    click.echo(f"\nTop {top} tecnologías:")
    for row in top_technologies(top=top, batch=batch):
        click.echo(f"  {row['tech']:<30} {row['count']}")
    close_db()


@main.command("detect")
@click.argument("url")
def detect_cmd(url: str) -> None:
    """Detecta tecnologías para una URL concreta, sin tocar la base de datos."""
    from .detection import detect_technologies

    _start_log("detect")
    wappalyzer = Wappalyzer.latest()
    tech = detect_technologies(url, wappalyzer=wappalyzer)
    if tech is None:
        click.echo(f"No se pudo acceder a {url}", err=True)
        sys.exit(1)
    for name in tech:
        click.echo(name)


if __name__ == "__main__":
    main()

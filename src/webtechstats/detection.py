# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Escaneo de tecnologías sobre los sitios pendientes de la colección `Site`."""

from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import Site
from .wappalyzer import Wappalyzer, WebPage

logger = logging.getLogger(__name__)

URL_CANDIDATES = ("https://{url}", "http://{url}", "https://www.{url}")


@dataclass
class ScanResult:
    processed: int = 0
    ok: int = 0
    failed: int = 0
    stopped: bool = False  # el escaneo se interrumpió a petición (se puede continuar relanzándolo)


def _detect(url: str, wappalyzer: Wappalyzer, timeout: int = 10) -> tuple[list[str] | None, str | None]:
    """Prueba las variantes https/http/www. Devuelve (tecnologías, None) o (None, clase del último error)."""
    reason = None
    for template in URL_CANDIDATES:
        candidate = template.format(url=url)
        try:
            webpage = WebPage.new_from_url(candidate, verify=False)
            return sorted(wappalyzer.analyze(webpage)), None
        except Exception as exc:
            reason = type(exc).__name__
            logger.debug("%s -> %s", candidate, reason)
    return None, reason or "SinRespuesta"


def detect_technologies(url: str, wappalyzer: Wappalyzer, timeout: int = 10) -> list[str] | None:
    """Intenta resolver `url` probando variantes https/http/www y devuelve las tecnologías
    detectadas, o None si ninguna variante respondió."""
    return _detect(url, wappalyzer, timeout)[0]


def _pending_sites(
    batch: int | None,
    limit: int,
    retry_failed: bool,
    max_retries: int | None,
    page_size: int,
    shard: tuple[int, int] | None = None,
):
    """Genera (id, url) de los sitios pendientes por posición, leyendo en páginas (paginación por
    posición: no se carga todo en memoria y los ya tratados nunca se vuelven a leer)."""
    filters: dict = {"finished": False}
    if batch is not None:
        filters["batch"] = batch
    if retry_failed:
        if max_retries is not None:
            filters["retries__lt"] = max_retries
    else:
        # lo ya intentado en este lote (descartado o con fallos previos) no se vuelve a escanear
        filters["retries"] = 0
        filters["discarded__ne"] = True
    last_position = None
    yielded = 0
    while yielded < limit:
        query = Site.objects(**filters)
        if last_position is not None:
            query = query.filter(position__gt=last_position)
        # Con trozos se lee la página completa y cada proceso se queda con los suyos (position % total == índice):
        # leer id/url/posición es barato frente a escanear, y evita depender de `$mod` en el servidor.
        size = page_size if shard else min(page_size, limit - yielded)
        page = list(query.order_by("position").limit(size).only("url", "position"))
        if not page:
            return
        last_position = page[-1].position
        mine = [s for s in page if shard is None or int(s.position) % shard[1] == shard[0]]
        for site in mine[: limit - yielded]:
            yield site.id, site.url
            yielded += 1


def scan_pending_sites(
    limit: int = 100,
    wappalyzer: Wappalyzer | None = None,
    batch: int | None = None,
    workers: int = 1,
    progress: Callable[[ScanResult], None] | None = None,
    max_retries: int | None = None,
    retry_failed: bool = False,
    should_stop: Callable[[], bool] | None = None,
    page_size: int = 1000,
    shard: tuple[int, int] | None = None,
) -> ScanResult:
    """Escanea hasta `limit` sitios pendientes, ordenados por posición, y guarda cada resultado en cuanto llega.

    - Un sitio ya intentado en su lote (con éxito o con fallo) no se vuelve a escanear; `retry_failed`
      reintenta los fallidos, y `max_retries` limita cuántas veces (solo con `retry_failed`).
    - `batch` limita el escaneo a un lote; el resto de lotes no se tocan.
    - `workers` peticiones HTTP en paralelo (ventana acotada: nunca hay más de `2 * workers` en vuelo).
      Las escrituras en MongoDB las hace siempre el hilo principal.
    - `should_stop` se consulta tras cada resultado; si devuelve True se deja de lanzar trabajo, se
      cancela lo que no ha empezado, se guardan los resultados en vuelo y se devuelve `stopped=True`.
      Lo no escaneado sigue pendiente, así que relanzar continúa donde se dejó.
    - `shard=(i, n)` limita el escaneo al trozo i de n (`position % n == i`): n procesos con trozos
      distintos escanean en paralelo sin solaparse ni coordinarse.
    - `progress` se invoca tras cada sitio procesado."""
    wappalyzer = wappalyzer or Wappalyzer.latest()
    result = ScanResult()
    sites = _pending_sites(batch, limit, retry_failed, max_retries, page_size, shard)
    urls: dict = {}

    def record(site_id, outcome) -> None:
        tech, reason = outcome
        now = datetime.now(timezone.utc)
        result.processed += 1
        if tech is None:
            Site.objects(id=site_id).update(
                inc__retries=1, set__discarded=True, set__discard_reason=reason, set__last_search_datetime=now
            )
            result.failed += 1
            logger.debug("sin respuesta: %s", urls.pop(site_id, site_id))
        else:
            Site.objects(id=site_id).update(
                set__tech=tech,
                set__finished=True,
                set__discarded=False,
                unset__discard_reason=True,
                set__last_search_datetime=now,
            )
            result.ok += 1
            logger.debug("OK %s: %d tecnologías", urls.pop(site_id, site_id), len(tech))
        if progress:
            progress(result)

    window = max(1, workers) * 2
    in_flight: dict = {}
    exhausted = False
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        while True:
            stopping = bool(should_stop and should_stop())
            while not stopping and not exhausted and len(in_flight) < window:
                nxt = next(sites, None)
                if nxt is None:
                    exhausted = True
                    break
                site_id, url = nxt
                urls[site_id] = url
                in_flight[pool.submit(_detect, url, wappalyzer)] = site_id
            if stopping:
                result.stopped = True
                for future in list(in_flight):
                    if future.cancel():  # lo que no ha empezado vuelve a quedar pendiente
                        urls.pop(in_flight.pop(future), None)
            if not in_flight:
                break
            done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
            for future in done:
                record(in_flight.pop(future), future.result())
    return result

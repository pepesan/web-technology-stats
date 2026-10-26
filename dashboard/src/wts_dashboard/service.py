# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Consultas del dashboard: rankings de tecnologías agrupados por tema."""

import time
from dataclasses import dataclass

from webtechstats.stats import batch_info
from webtechstats.stats import summary, top_technologies
from webtechstats.topics import TOPICS, TopicClassifier


@dataclass(frozen=True)
class Entry:
    tech: str
    count: int
    topic: str
    category: str


class DashboardService:
    def __init__(self, classifier: TopicClassifier | None = None, cache_ttl: float = 30.0):
        self._classifier = classifier
        self._cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, dict]] = {}

    @property
    def classifier(self) -> TopicClassifier:
        if self._classifier is None:
            self._classifier = TopicClassifier.latest()
        return self._classifier

    def batches(self) -> list[dict]:
        return batch_info()

    def _load(self, batch: int | None, max_position: int | None = None, tld: str | None = None) -> dict:
        """Resumen + ranking completo clasificado por tema (cacheado unos segundos)."""
        key = (batch, max_position, tld)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self._cache_ttl:
            return cached[1]
        data = summary(batch=batch, max_position=max_position, tld=tld)
        entries = [
            Entry(r["tech"], r["count"], self.classifier.topic(r["tech"]), self.classifier.category(r["tech"]))
            for r in top_technologies(top=None, batch=batch, max_position=max_position, tld=tld)
        ]
        loaded = {"summary": data, "entries": entries}
        self._cache[key] = (time.monotonic(), loaded)
        return loaded

    @staticmethod
    def _pct(count: int, base: int) -> float:
        return round(100 * count / base, 1) if base else 0.0

    def overview(self, batch: int | None = None, max_position: int | None = None, tld: str | None = None) -> dict:
        loaded = self._load(batch, max_position, tld)
        data, entries = loaded["summary"], loaded["entries"]
        topics = []
        for key, label in TOPICS.items():
            of_topic = [e for e in entries if e.topic == key]
            topics.append(
                {
                    "key": key,
                    "label": label,
                    "distinct": len(of_topic),
                    "top": [
                        {"tech": e.tech, "count": e.count, "pct": self._pct(e.count, data["finished"])}
                        for e in of_topic[:3]
                    ],
                }
            )
        return {
            "batch": batch,
            "max_position": max_position,
            "tld": tld,
            "total": data["total"],
            "finished": data["finished"],
            "pending": data["pending"],
            "failed": data["failed"],
            "with_tech": data["finished_with_tech"],
            "distinct_tech": len(entries),
            "topics": topics,
        }

    def topic_ranking(
        self,
        topic: str,
        batch: int | None = None,
        limit: int = 15,
        category: str | None = None,
        max_position: int | None = None,
        tld: str | None = None,
    ) -> dict:
        """Ranking de un tema. Lanza KeyError si el tema no existe."""
        label = TOPICS[topic]
        loaded = self._load(batch, max_position, tld)
        base = loaded["summary"]["finished"]
        of_topic = [e for e in loaded["entries"] if e.topic == topic]
        categories = sorted({e.category for e in of_topic if e.category})
        if category:
            of_topic = [e for e in of_topic if e.category == category]
        return {
            "topic": topic,
            "label": label,
            "batch": batch,
            "max_position": max_position,
            "tld": tld,
            "base": base,
            "total_items": len(of_topic),
            "categories": categories,
            "items": [
                {"tech": e.tech, "count": e.count, "pct": self._pct(e.count, base), "category": e.category}
                for e in of_topic[:limit]
            ],
        }

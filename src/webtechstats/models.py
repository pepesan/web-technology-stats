"""Modelos mongoengine."""

from datetime import datetime, timezone

from mongoengine import (
    BooleanField,
    DateTimeField,
    DecimalField,
    Document,
    ListField,
    StringField,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Site(Document):
    # Un mismo dominio puede existir una vez por lote: cada lote conserva sus propios resultados.
    url = StringField(required=True, unique_with="batch")
    position = DecimalField(required=True)
    batch = DecimalField(required=True, default=1)
    retries = DecimalField(required=True, default=0)
    tech = ListField(StringField(max_length=120))
    last_search_datetime = DateTimeField(default=_utcnow)
    finished = BooleanField(default=False)
    # Sitio descartado: se intentó y no se pudieron extraer tecnologías. No se vuelve a escanear
    # salvo con `scan --retry-failed`. `discard_reason` guarda la clase del último error.
    discarded = BooleanField(default=False)
    discard_reason = StringField()

    meta = {
        "collection": "site",
        "indexes": [
            "finished",
            "position",
            "tech",
            "retries",
            "batch",
            "discarded",
        ],
    }

    @classmethod
    def ensure_schema(cls) -> None:
        """Asegura los índices, migrando el esquema antiguo (`url` único a secas)."""
        collection = cls._get_collection()
        legacy = collection.index_information().get("url_1")
        if legacy and legacy.get("unique"):
            collection.drop_index("url_1")
        cls.ensure_indexes()
        # Fallos anteriores al campo `discarded`: se marcan como descartados (idempotente).
        collection.update_many(
            {"finished": False, "retries": {"$gt": 0}, "discarded": {"$ne": True}},
            {"$set": {"discarded": True, "discard_reason": "desconocido"}},
        )

    def __str__(self) -> str:
        return f"{self.url}:{self.tech}"

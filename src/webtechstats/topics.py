# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Clasificación de tecnologías por tema (lenguajes de back/front, BBDD, librerías...).

`Site.tech` solo guarda nombres; el tema se deduce de las categorías de `apps.json`,
así que cambiar esta clasificación no obliga a re-escanear nada.
"""

from .wappalyzer import Wappalyzer

# Orden de presentación de las pestañas del dashboard.
TOPICS: dict[str, str] = {
    "lang_back": "Lenguajes de back",
    "lang_front": "Lenguajes de front",
    "back_libs": "Frameworks y librerías de back",
    "front_libs": "Frameworks y librerías de front",
    "databases": "Bases de datos",
    "other": "Otras tecnologías",
}

# La categoría 27 de Wappalyzer ("Programming languages") mezcla lenguajes de back y de front:
# los que solo tienen sentido en el navegador se separan por nombre.
FRONT_LANGUAGES = frozenset({"TypeScript", "Dart", "Elm", "Sass", "WebAssembly", "Adobe Flash", "XSLT"})

# id de categoría de Wappalyzer -> tema.
CATEGORY_TOPICS: dict[int, str] = {
    27: "lang_back",
    34: "databases",
    3: "databases",
    12: "front_libs",
    59: "front_libs",
    66: "front_libs",
    25: "front_libs",
    26: "front_libs",
    18: "back_libs",
}
# Si una tecnología tiene varias categorías gana el tema más a la izquierda
# (p. ej. Chosen está en "JavaScript frameworks" y "Web frameworks": se considera de front).
_TOPIC_PRIORITY = ("lang_back", "databases", "front_libs", "back_libs")


class TopicClassifier:
    def __init__(self, categories: dict, apps: dict):
        self._category_names = {
            int(cid): (c["name"] if isinstance(c, dict) else str(c)) for cid, c in categories.items()
        }
        self._apps = apps

    @classmethod
    def latest(cls) -> "TopicClassifier":
        w = Wappalyzer.latest()
        return cls(w.categories, w.apps)

    def category(self, tech: str) -> str:
        """Nombre de la primera categoría de la tecnología ('' si es desconocida)."""
        cats = self._apps.get(tech, {}).get("cats", [])
        return self._category_names.get(cats[0], "") if cats else ""

    def topic(self, tech: str) -> str:
        cats = self._apps.get(tech, {}).get("cats", [])
        topics = {CATEGORY_TOPICS[c] for c in cats if c in CATEGORY_TOPICS}
        if "lang_back" in topics and tech in FRONT_LANGUAGES:
            return "lang_front"
        for topic in _TOPIC_PRIORITY:
            if topic in topics:
                return topic
        return "other"

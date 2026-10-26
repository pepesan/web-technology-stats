import pytest

from webtechstats.models import Site
from webtechstats.stats import batches, top_technologies
from webtechstats.topics import TOPICS, TopicClassifier


@pytest.fixture(scope="module")
def classifier():
    return TopicClassifier.latest()


@pytest.mark.parametrize(
    "tech, topic",
    [
        ("PHP", "lang_back"),
        ("Python", "lang_back"),
        ("TypeScript", "lang_front"),  # categoría 27, pero lenguaje de front
        ("Sass", "lang_front"),
        ("Laravel", "back_libs"),
        ("Django", "back_libs"),
        ("React", "front_libs"),
        ("jQuery", "front_libs"),
        ("Chosen", "front_libs"),  # en front y back: gana front
        ("MySQL", "databases"),
        ("PostgreSQL", "databases"),
        ("Nginx", "other"),
        ("WordPress", "other"),
        ("TecnologiaInexistente", "other"),
    ],
)
def test_topic(classifier, tech, topic):
    assert classifier.topic(tech) == topic


def test_every_topic_is_reachable_and_labelled(classifier):
    assert {classifier.topic(t) for t in ("PHP", "TypeScript", "Laravel", "React", "MySQL", "Nginx")} == set(TOPICS)


def test_category_name(classifier):
    assert classifier.category("Nginx") == "Web servers"
    assert classifier.category("TecnologiaInexistente") == ""


def test_batches_sorted_and_distinct(db):
    Site(url="a.com", position=1, batch=2).save()
    Site(url="a.com", position=1, batch=1).save()
    Site(url="b.com", position=2, batch=1).save()
    assert batches() == [1, 2]


def test_top_technologies_without_limit_returns_all(db):
    Site(url="a.com", position=1, finished=True, tech=["A", "B", "C"]).save()
    assert len(top_technologies(top=None)) == 3
    assert len(top_technologies(top=2)) == 2


def test_batch_info_per_execution(db):
    Site(url="a.com", position=1, batch=1, finished=True).save()
    Site(url="b.com", position=2, batch=1).save()
    Site(url="a.com", position=1, batch=2, finished=True).save()
    from webtechstats.stats import batch_info

    Site(url="c.com", position=3, batch=2, retries=3).save()
    info = batch_info()
    assert [(b["batch"], b["total"], b["finished"], b["failed"]) for b in info] == [(1, 2, 1, 0), (2, 2, 1, 1)]
    assert info[0]["last_activity"]

import json

import pytest
from conftest import seed
from wts_dashboard.report import TOP_STEPS, export_report, main
from wts_dashboard.service import DashboardService


@pytest.fixture
def service(db):
    return DashboardService(cache_ttl=3600)


def read(path):
    return json.loads(path.read_text())


def test_top_steps_follow_the_dashboard_filter():
    assert TOP_STEPS == [100, 1_000, 10_000, 100_000, 200_000, 300_000, 400_000, 500_000, 600_000,
                         700_000, 800_000, 900_000, 1_000_000]


def test_export_writes_one_file_per_cut_plus_all(service, tmp_path):
    seed()
    entry = export_report(service, report_id="2026", label="Tranco 2026", batch=1, out_dir=tmp_path, year=2026)
    # El lote 1 tiene 4 sitios: ningún corte estándar (100...) cabe, pero "todos" siempre se escribe.
    assert entry["tops"] == []
    assert [p.name for p in (tmp_path / "2026").iterdir()] == ["top-all.json"]
    export_report(service, "cuts", "Cortes", batch=1, out_dir=tmp_path, steps=[2, 4, 100])
    assert sorted(p.name for p in (tmp_path / "cuts").iterdir()) == ["top-2.json", "top-4.json", "top-all.json"]


def test_cut_file_has_summary_and_full_ranking_per_topic(service, tmp_path):
    seed()
    export_report(service, "2026", "Tranco 2026", batch=1, out_dir=tmp_path, year=2026)
    data = read(tmp_path / "2026" / "top-all.json")
    assert data["report"] == "2026" and data["max_position"] is None
    assert (data["summary"]["total"], data["summary"]["finished"], data["summary"]["pending"]) == (4, 3, 1)
    topics = {t["key"]: t for t in data["topics"]}
    assert list(topics) == ["lang_back", "lang_front", "back_libs", "front_libs", "databases", "other"]
    assert [i["tech"] for i in topics["lang_back"]["items"]][:2] == ["PHP", "Python"]
    assert topics["lang_back"]["items"][0] == {"tech": "PHP", "count": 2, "pct": 66.7, "category": "Programming languages"}
    assert topics["lang_back"]["distinct"] == len(topics["lang_back"]["items"])
    assert {i["tech"] for i in topics["databases"]["items"]} == {"MySQL", "PostgreSQL"}
    assert "Databases" in topics["databases"]["categories"]


def test_cut_limits_to_the_top_positions(service, tmp_path):
    seed()
    export_report(service, "2026", "Tranco 2026", batch=1, out_dir=tmp_path, year=2026)
    export_report(service, "tiny", "Tiny", batch=1, out_dir=tmp_path, year=2026, steps=[2])
    cut = read(tmp_path / "tiny" / "top-2.json")
    assert cut["max_position"] == 2 and cut["summary"]["total"] == 2
    assert {i["tech"] for t in cut["topics"] for i in t["items"]} <= {"PHP", "MySQL", "jQuery", "Nginx", "React", "TypeScript", "Laravel"}


def test_index_lists_reports_and_replaces_same_id(service, tmp_path):
    seed()
    export_report(service, "2026", "Tranco 2026", batch=1, out_dir=tmp_path, year=2026)
    export_report(service, "2027", "Tranco 2027", batch=2, out_dir=tmp_path, year=2027)
    export_report(service, "2026", "Tranco 2026 (rev)", batch=1, out_dir=tmp_path, year=2026)
    index = read(tmp_path / "index.json")
    assert [r["id"] for r in index["reports"]] == ["2026", "2027"]
    first = index["reports"][0]
    assert first["label"] == "Tranco 2026 (rev)" and first["year"] == 2026 and first["batch"] == 1
    assert (first["total"], first["finished"], first["failed"]) == (4, 3, 0)
    assert "sites" not in json.dumps(index) and "a.com" not in json.dumps(index)


def test_export_contains_no_domains(service, tmp_path):
    seed()
    export_report(service, "2026", "Tranco 2026", batch=1, out_dir=tmp_path, year=2026)
    blob = "".join(p.read_text() for p in (tmp_path / "2026").iterdir())
    assert ".com" not in blob


def test_unknown_or_empty_batch_is_refused(service, tmp_path):
    seed()
    with pytest.raises(ValueError, match="lote"):
        export_report(service, "x", "x", batch=99, out_dir=tmp_path)


def test_report_id_must_be_a_safe_name(service, tmp_path):
    seed()
    for bad in ["", "../x", "a/b", ".hidden"]:
        with pytest.raises(ValueError, match="identificador"):
            export_report(service, bad, "x", batch=1, out_dir=tmp_path)


def test_cli_exports_with_arguments(db, tmp_path, monkeypatch):
    seed()
    monkeypatch.setattr("wts_dashboard.report.connect_db", lambda: None)
    monkeypatch.setattr("wts_dashboard.report.disconnect_db", lambda: None)
    assert main(["--batch", "1", "--id", "2026", "--label", "Tranco 2026", "--year", "2026", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "index.json").is_file()

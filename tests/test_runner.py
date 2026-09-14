"""Tests for duckcheck runner."""

import sqlite3
from pathlib import Path

import pytest
import yaml

from duckcheck.runner import run_suite, to_junit, update_baseline
from duckcheck.spec import CheckSpec, SuiteSpec

ROOT = Path(__file__).parent.parent
EXAMPLE = ROOT / "examples" / "checks.yaml"


def test_sample_suite_fails_on_null_name() -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    suite = SuiteSpec.model_validate(raw)
    report = run_suite(suite, suite_dir=EXAMPLE.parent)
    assert not report.passed
    failed = [r for r in report.results if not r.passed]
    assert any(r.name == "name_not_null" for r in failed)
    assert any(r.name == "at_least_one_row" and r.passed for r in report.results)


def test_junit_contains_failures() -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    suite = SuiteSpec.model_validate(raw)
    report = run_suite(suite, suite_dir=EXAMPLE.parent)
    xml = to_junit(report)
    assert "testcase" in xml
    assert "failure" in xml


def test_sqlite_source_and_row_count_delta(tmp_path: Path) -> None:
    db = tmp_path / "orders.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE orders (id INTEGER, name TEXT)")
    conn.executemany("INSERT INTO orders VALUES (?, ?)", [(1, "a"), (2, "b"), (3, "c")])
    conn.commit()
    conn.close()

    suite = SuiteSpec(
        name="sqlite-suite",
        source=f"sqlite://{db}",
        source_table="orders",
        baseline=str(tmp_path / "baseline.db"),
        checks=[
            CheckSpec(name="volume", type="row_count_delta", tolerance_pct=10),
            CheckSpec(name="ids", type="not_null", column="id"),
        ],
    )
    first = run_suite(suite, suite_dir=tmp_path)
    assert any(r.name == "volume" and not r.passed for r in first.results)
    update_baseline(suite, suite_dir=tmp_path)
    second = run_suite(suite, suite_dir=tmp_path)
    assert second.passed


def test_clean_suite_passes() -> None:
    example = ROOT / "examples" / "clean.yaml"
    raw = yaml.safe_load(example.read_text())
    suite = SuiteSpec.model_validate(raw)
    report = run_suite(suite, suite_dir=example.parent)
    assert report.passed


def test_missing_source_raises(tmp_path: Path) -> None:
    suite = SuiteSpec(
        name="missing",
        source="no-such-file.csv",
        checks=[CheckSpec(name="ids", type="not_null", column="id")],
    )
    with pytest.raises(FileNotFoundError, match="Source not found"):
        run_suite(suite, suite_dir=tmp_path)


def test_freshness_respects_frozen_now(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUCKCHECK_NOW", "2020-01-02 00:00:00")
    csv_path = tmp_path / "events.csv"
    csv_path.write_text("id,updated_at\n1,2020-01-01 00:00:00\n", encoding="utf-8")
    suite = SuiteSpec(
        name="fresh",
        source=str(csv_path),
        checks=[CheckSpec(name="stale", type="freshness", column="updated_at", max_age="12h")],
    )
    report = run_suite(suite, suite_dir=tmp_path)
    assert not report.passed
    assert report.results[0].rows_failed == 1


def test_custom_sql_expect_operators(tmp_path: Path) -> None:
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("id,amount\n1,10\n2,20\n3,30\n", encoding="utf-8")
    suite = SuiteSpec(
        name="expect",
        source=str(csv_path),
        checks=[
            CheckSpec(
                name="three_rows",
                type="custom_sql",
                sql="SELECT * FROM source_data",
                expect="=3",
            ),
            CheckSpec(
                name="has_high",
                type="custom_sql",
                sql="SELECT * FROM source_data WHERE amount > 15",
                expect=">0",
            ),
            CheckSpec(
                name="no_negatives",
                type="custom_sql",
                sql="SELECT * FROM source_data WHERE amount < 0",
                expect="0",
            ),
        ],
    )
    report = run_suite(suite, suite_dir=tmp_path)
    assert report.passed

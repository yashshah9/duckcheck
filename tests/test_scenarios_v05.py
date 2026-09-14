"""v0.5 robustness scenarios — CSV/YAML suites via tmp_path."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import duckdb
import pytest
import yaml

from duckcheck.runner import run_suite, to_junit, update_baseline
from duckcheck.spec import CheckSpec, SuiteSpec


def _write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_suite(path: Path, suite: dict) -> SuiteSpec:
    path.write_text(yaml.safe_dump(suite, sort_keys=False), encoding="utf-8")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SuiteSpec.model_validate(raw)


def _run(suite: SuiteSpec | dict, tmp_path: Path) -> object:
    if isinstance(suite, dict):
        yaml_path = tmp_path / "suite.yaml"
        spec = _write_suite(yaml_path, suite)
        return run_suite(spec, suite_dir=tmp_path)
    return run_suite(suite, suite_dir=tmp_path)


def _result(report: object, name: str):
    return next(r for r in report.results if r.name == name)


def _json_payload(report: object) -> dict:
    """Mirror duckcheck run --format json output from RunReport."""
    return {
        "suite": report.suite,
        "passed": report.passed,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "message": r.message,
                "rows_failed": r.rows_failed,
            }
            for r in report.results
        ],
    }


# --- pattern ---


def test_pattern_passes_valid_values(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,code\n1,ABC\n2,DEF\n")
    report = _run(
        {
            "name": "pattern-pass",
            "source": csv.name,
            "checks": [
                {"name": "code_fmt", "type": "pattern", "column": "code", "pattern": r"^[A-Z]{3}$"}
            ],
        },
        tmp_path,
    )
    assert _result(report, "code_fmt").passed


def test_pattern_fails_on_invalid_values(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,code\n1,ABC\n2,bad\n")
    report = _run(
        {
            "name": "pattern-fail",
            "source": csv.name,
            "checks": [
                {"name": "code_fmt", "type": "pattern", "column": "code", "pattern": r"^[A-Z]{3}$"}
            ],
        },
        tmp_path,
    )
    r = _result(report, "code_fmt")
    assert not r.passed
    assert r.rows_failed == 1
    assert "do not match pattern" in r.message


def test_pattern_ignores_null_values(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,email\n1,ok@x.com\n2,\n3,bad\n")
    report = _run(
        {
            "name": "pattern-nulls",
            "source": csv.name,
            "checks": [
                {
                    "name": "email_shape",
                    "type": "pattern",
                    "column": "email",
                    "pattern": r"^[^@]+@[^@]+\.[^@]+$",
                }
            ],
        },
        tmp_path,
    )
    r = _result(report, "email_shape")
    assert not r.passed
    assert r.rows_failed == 1  # only "bad", null ignored


# --- custom_sql substitution ---


def test_custom_sql_column_substitution(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,score\n1,10\n2,\n")
    report = _run(
        SuiteSpec(
            name="sub-col",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="null_scores",
                    type="custom_sql",
                    column="score",
                    sql="SELECT * FROM source_data WHERE ${column} IS NULL",
                    expect="=1",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "null_scores").passed


def test_custom_sql_name_substitution(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        SuiteSpec(
            name="sub-name",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="two_rows",
                    type="custom_sql",
                    sql="SELECT * FROM source_data WHERE '${name}' = 'two_rows'",
                    expect="=2",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "two_rows").passed


def test_custom_sql_unknown_placeholder_left_intact(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n")
    suite = SuiteSpec(
        name="sub-unknown",
        source=str(csv),
        checks=[
            CheckSpec(
                name="bad_token",
                type="custom_sql",
                sql="SELECT * FROM source_data WHERE ${foo} IS NULL",
                expect="0",
            )
        ],
    )
    with pytest.raises(duckdb.Error, match=r"\$\{foo\}"):
        run_suite(suite, suite_dir=tmp_path)


# --- expect operators ---


def test_expect_equals_zero(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        SuiteSpec(
            name="eq0",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="no_dups",
                    type="custom_sql",
                    sql="SELECT id FROM source_data GROUP BY id HAVING COUNT(*) > 1",
                    expect="0",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "no_dups").passed


def test_expect_equals_n_pass(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n3\n")
    report = _run(
        SuiteSpec(
            name="eqn",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="three",
                    type="custom_sql",
                    sql="SELECT * FROM source_data",
                    expect="=3",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "three").passed


def test_expect_equals_n_fail(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        SuiteSpec(
            name="eqn-fail",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="three",
                    type="custom_sql",
                    sql="SELECT * FROM source_data",
                    expect="=3",
                )
            ],
        ),
        tmp_path,
    )
    assert not _result(report, "three").passed


def test_expect_gt_zero(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,amount\n1,5\n2,10\n")
    report = _run(
        SuiteSpec(
            name="gt0",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="has_big",
                    type="custom_sql",
                    sql="SELECT * FROM source_data WHERE amount > 7",
                    expect=">0",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "has_big").passed


def test_expect_lt_n(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        SuiteSpec(
            name="ltn",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="few",
                    type="custom_sql",
                    sql="SELECT * FROM source_data",
                    expect="<5",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "few").passed


def test_expect_gte_edge(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        SuiteSpec(
            name="gte",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="at_least_two",
                    type="custom_sql",
                    sql="SELECT * FROM source_data",
                    expect=">=2",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "at_least_two").passed


def test_expect_lte_edge(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        SuiteSpec(
            name="lte",
            source=str(csv),
            checks=[
                CheckSpec(
                    name="at_most_two",
                    type="custom_sql",
                    sql="SELECT * FROM source_data",
                    expect="<=2",
                )
            ],
        ),
        tmp_path,
    )
    assert _result(report, "at_most_two").passed


# --- column checks ---


def test_not_null_pass_and_fail(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,name\n1,alice\n2,\n")
    report = _run(
        {
            "name": "not-null",
            "source": csv.name,
            "checks": [
                {"name": "id_ok", "type": "not_null", "column": "id"},
                {"name": "name_ok", "type": "not_null", "column": "name"},
            ],
        },
        tmp_path,
    )
    assert _result(report, "id_ok").passed
    assert not _result(report, "name_ok").passed
    assert _result(report, "name_ok").rows_failed == 1


def test_unique_pass_and_fail(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,tag\n1,a\n2,b\n3,a\n")
    report = _run(
        {
            "name": "unique",
            "source": csv.name,
            "checks": [
                {"name": "id_unique", "type": "unique", "column": "id"},
                {"name": "tag_unique", "type": "unique", "column": "tag"},
            ],
        },
        tmp_path,
    )
    assert _result(report, "id_unique").passed
    assert not _result(report, "tag_unique").passed


def test_accepted_values_pass_and_fail(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,status\n1,active\n2,pending\n")
    report = _run(
        {
            "name": "accepted",
            "source": csv.name,
            "checks": [
                {
                    "name": "status_ok",
                    "type": "accepted_values",
                    "column": "status",
                    "values": ["active", "inactive"],
                }
            ],
        },
        tmp_path,
    )
    r = _result(report, "status_ok")
    assert not r.passed
    assert r.rows_failed == 1


def test_row_count_min_max_bounds(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n3\n")
    ok = _run(
        {
            "name": "bounds-ok",
            "source": csv.name,
            "checks": [{"name": "size", "type": "row_count", "min_rows": 2, "max_rows": 5}],
        },
        tmp_path,
    )
    assert _result(ok, "size").passed

    bad = _run(
        {
            "name": "bounds-bad",
            "source": csv.name,
            "checks": [{"name": "size", "type": "row_count", "min_rows": 5, "max_rows": 10}],
        },
        tmp_path,
    )
    assert not _result(bad, "size").passed


# --- freshness ---


def test_freshness_stale_with_frozen_now(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUCKCHECK_NOW", "2020-01-02 00:00:00")
    csv = _write_csv(tmp_path / "data.csv", "id,updated_at\n1,2020-01-01 00:00:00\n")
    report = _run(
        {
            "name": "stale",
            "source": csv.name,
            "checks": [
                {"name": "fresh_enough", "type": "freshness", "column": "updated_at", "max_age": "12h"}
            ],
        },
        tmp_path,
    )
    r = _result(report, "fresh_enough")
    assert not r.passed
    assert r.rows_failed == 1


def test_freshness_passes_when_within_max_age(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUCKCHECK_NOW", "2020-01-01 06:00:00")
    csv = _write_csv(tmp_path / "data.csv", "id,updated_at\n1,2020-01-01 00:00:00\n")
    report = _run(
        {
            "name": "fresh",
            "source": csv.name,
            "checks": [
                {"name": "fresh_enough", "type": "freshness", "column": "updated_at", "max_age": "12h"}
            ],
        },
        tmp_path,
    )
    assert _result(report, "fresh_enough").passed


# --- junit / json ---


def test_junit_contains_failure_elements(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,name\n1,\n")
    report = _run(
        {
            "name": "junit-fail",
            "source": csv.name,
            "checks": [{"name": "name_ok", "type": "not_null", "column": "name"}],
        },
        tmp_path,
    )
    xml = to_junit(report)
    assert "testcase" in xml
    assert "failure" in xml
    assert 'name="name_ok"' in xml


def test_junit_passing_suite_has_zero_failures(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id,name\n1,alice\n")
    report = _run(
        {
            "name": "junit-pass",
            "source": csv.name,
            "checks": [{"name": "name_ok", "type": "not_null", "column": "name"}],
        },
        tmp_path,
    )
    xml = to_junit(report)
    assert 'failures="0"' in xml
    assert "<failure" not in xml


def test_report_serializes_to_json(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n")
    report = _run(
        {"name": "json", "source": csv.name, "checks": [{"name": "ids", "type": "not_null", "column": "id"}]},
        tmp_path,
    )
    payload = _json_payload(report)
    text = json.dumps(payload)
    parsed = json.loads(text)
    assert parsed["suite"] == "json"
    assert parsed["passed"] is True
    assert parsed["results"][0]["name"] == "ids"
    assert "rows_failed" in parsed["results"][0]


# --- baseline / row_count_delta ---


def test_row_count_delta_fails_without_baseline(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n")
    report = _run(
        {
            "name": "delta-no-base",
            "source": csv.name,
            "baseline": "baseline.db",
            "checks": [{"name": "volume", "type": "row_count_delta", "tolerance_pct": 10}],
        },
        tmp_path,
    )
    r = _result(report, "volume")
    assert not r.passed
    assert "no baseline" in r.message


def test_baseline_update_then_delta_passes(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n3\n")
    suite = SuiteSpec(
        name="delta-ok",
        source=str(csv),
        baseline=str(tmp_path / "baseline.db"),
        checks=[CheckSpec(name="volume", type="row_count_delta", tolerance_pct=10)],
    )
    first = run_suite(suite, suite_dir=tmp_path)
    assert not _result(first, "volume").passed
    update_baseline(suite, suite_dir=tmp_path)
    second = run_suite(suite, suite_dir=tmp_path)
    assert _result(second, "volume").passed


def test_row_count_delta_fails_on_drift(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", "id\n1\n2\n3\n4\n5\n")
    suite = SuiteSpec(
        name="delta-drift",
        source=str(csv),
        baseline=str(tmp_path / "baseline.db"),
        checks=[CheckSpec(name="volume", type="row_count_delta", tolerance_pct=10)],
    )
    update_baseline(suite, suite_dir=tmp_path)
    csv.write_text("id\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n", encoding="utf-8")
    report = run_suite(suite, suite_dir=tmp_path)
    r = _result(report, "volume")
    assert not r.passed
    assert "drift" in r.message


def test_yaml_suite_roundtrip_via_tmp_path(tmp_path: Path) -> None:
    _write_csv(tmp_path / "orders.csv", "id,status\n1,active\n2,active\n")
    suite_dict = {
        "name": "yaml-roundtrip",
        "source": "orders.csv",
        "checks": [
            {"name": "id_not_null", "type": "not_null", "column": "id"},
            {"name": "status_values", "type": "accepted_values", "column": "status", "values": ["active"]},
        ],
    }
    yaml_path = tmp_path / "checks.yaml"
    _write_suite(yaml_path, suite_dict)
    loaded = SuiteSpec.model_validate(yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    report = run_suite(loaded, suite_dir=tmp_path)
    assert report.passed


def test_sqlite_source_with_row_count_delta(tmp_path: Path) -> None:
    db = tmp_path / "data.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE items (id INTEGER)")
    conn.executemany("INSERT INTO items VALUES (?)", [(1,), (2,), (3,)])
    conn.commit()
    conn.close()

    suite = SuiteSpec(
        name="sqlite-delta",
        source=f"sqlite://{db}",
        source_table="items",
        baseline=str(tmp_path / "baseline.db"),
        checks=[CheckSpec(name="volume", type="row_count_delta", tolerance_pct=10)],
    )
    assert not _result(run_suite(suite, suite_dir=tmp_path), "volume").passed
    update_baseline(suite, suite_dir=tmp_path)
    assert _result(run_suite(suite, suite_dir=tmp_path), "volume").passed

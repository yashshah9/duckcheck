"""Tests for orchestrator helpers (no Airflow/Dagster required)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from duckcheck.orchestrate import execute_suite_path, report_summary
from duckcheck.runner import CheckResult, RunReport


def _write_suite(path: Path, *, source: str, bad: bool = False) -> Path:
    suite = {
        "name": "orch",
        "source": source,
        "checks": [
            {"name": "rows", "type": "row_count", "min_rows": 1},
            {
                "name": "status_ok",
                "type": "accepted_values",
                "column": "status",
                "values": ["active"] if bad else ["active", "inactive"],
            },
        ],
    }
    path.write_text(yaml.safe_dump(suite), encoding="utf-8")
    return path


def test_execute_suite_path_pass(tmp_path: Path) -> None:
    csv = tmp_path / "data.csv"
    csv.write_text("id,status\n1,active\n2,inactive\n", encoding="utf-8")
    suite = _write_suite(tmp_path / "suite.yaml", source=str(csv))
    junit = tmp_path / "out.xml"
    summary = execute_suite_path(suite, junit_output=junit)
    assert summary["passed"] is True
    assert summary["passed_count"] == 2
    assert summary["failed_count"] == 0
    assert junit.is_file()
    assert "testcase" in junit.read_text(encoding="utf-8")


def test_execute_suite_path_fail_and_source_override(tmp_path: Path) -> None:
    good = tmp_path / "good.csv"
    bad = tmp_path / "bad.csv"
    good.write_text("id,status\n1,active\n", encoding="utf-8")
    bad.write_text("id,status\n1,nope\n", encoding="utf-8")
    suite = _write_suite(tmp_path / "suite.yaml", source=str(good), bad=True)
    # override to bad file → accepted_values fails
    summary = execute_suite_path(suite, source=str(bad))
    assert summary["passed"] is False
    assert summary["failed_count"] >= 1


def test_execute_suite_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        execute_suite_path(tmp_path / "missing.yaml")


def test_report_summary_shape() -> None:
    report = RunReport(
        suite="s",
        results=[
            CheckResult(name="a", passed=True, message="ok"),
            CheckResult(name="b", passed=False, message="bad", rows_failed=2),
        ],
    )
    summary = report_summary(report)
    assert summary["passed"] is False
    assert summary["passed_count"] == 1
    assert summary["failed_count"] == 1


def test_airflow_operator_import_message() -> None:
    # Without airflow installed in the test image, import should explain the extra.
    try:
        import airflow  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError, match="duckcheck\\[airflow\\]"):
            import duckcheck.airflow_op  # noqa: F401
    else:
        from duckcheck.airflow_op import DuckCheckOperator

        assert DuckCheckOperator.__name__ == "DuckCheckOperator"


def test_dagster_op_import_message() -> None:
    try:
        import dagster  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError, match="duckcheck\\[dagster\\]"):
            import duckcheck.dagster_op  # noqa: F401
    else:
        from duckcheck.dagster_op import duckcheck_op

        assert callable(duckcheck_op)

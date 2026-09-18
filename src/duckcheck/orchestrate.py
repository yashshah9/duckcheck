"""Shared suite execution helpers for CLI and orchestrators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from duckcheck.runner import RunReport, run_suite, to_junit
from duckcheck.spec import SuiteSpec


def load_suite(suite_path: Path) -> SuiteSpec:
    raw = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    return SuiteSpec.model_validate(raw)


def report_summary(report: RunReport) -> dict[str, Any]:
    return {
        "suite": report.suite,
        "passed": report.passed,
        "passed_count": sum(1 for r in report.results if r.passed),
        "failed_count": sum(1 for r in report.results if not r.passed),
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


def execute_suite_path(
    suite_path: str | Path,
    *,
    source: str | None = None,
    source_table: str | None = None,
    junit_output: str | Path | None = None,
) -> dict[str, Any]:
    """Load a suite YAML, optionally override source, run checks, return summary.

    Used by Airflow/Dagster operators so orchestration deps stay optional.
    """
    path = Path(suite_path)
    if not path.exists():
        raise FileNotFoundError(f"Suite not found: {path}")
    try:
        suite = load_suite(path)
    except (yaml.YAMLError, ValidationError, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid suite: {exc}") from exc
    if source is not None:
        suite.source = source
    if source_table is not None:
        suite.source_table = source_table
    report = run_suite(suite, suite_dir=path.parent)
    if junit_output is not None:
        out = Path(junit_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_junit(report), encoding="utf-8")
    return report_summary(report)

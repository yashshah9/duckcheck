"""Dagster op factory for duckcheck (optional extra: duckcheck[dagster])."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from duckcheck.orchestrate import execute_suite_path

try:
    from dagster import MetadataValue, OpExecutionContext, Out, Output, op
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "duckcheck Dagster support requires Dagster. "
        "Install with: pip install 'duckcheck[dagster]'"
    ) from exc


def duckcheck_op(
    *,
    name: str = "duckcheck",
    suite_path: str,
    source: str | None = None,
    source_table: str | None = None,
    junit_output: str | None = None,
    fail_on_error: bool = True,
) -> Callable[..., Any]:
    """Build a Dagster ``@op`` that runs a duckcheck suite.

    Emits metadata: passed, passed_count, failed_count. Raises on failure when
    ``fail_on_error`` is true.
    """

    @op(name=name, out=Out(dict))
    def _run(context: OpExecutionContext) -> Output[dict[str, Any]]:
        summary = execute_suite_path(
            suite_path,
            source=source,
            source_table=source_table,
            junit_output=junit_output,
        )
        meta = {
            "suite": MetadataValue.text(str(summary["suite"])),
            "passed": MetadataValue.bool(bool(summary["passed"])),
            "passed_count": MetadataValue.int(int(summary["passed_count"])),
            "failed_count": MetadataValue.int(int(summary["failed_count"])),
        }
        if fail_on_error and not summary["passed"]:
            raise RuntimeError(
                f"duckcheck suite {summary['suite']!r} failed: "
                f"{summary['failed_count']} check(s) failed"
            )
        return Output(summary, metadata=meta)

    return _run

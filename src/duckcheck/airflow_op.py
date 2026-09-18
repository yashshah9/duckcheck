"""Apache Airflow operator for duckcheck (optional extra: duckcheck[airflow])."""

from __future__ import annotations

from typing import Any

from duckcheck.orchestrate import execute_suite_path

try:
    from airflow.exceptions import AirflowException
    from airflow.models.baseoperator import BaseOperator
except ImportError as exc:  # pragma: no cover - exercised when extra missing
    raise ImportError(
        "duckcheck Airflow support requires Apache Airflow. "
        "Install with: pip install 'duckcheck[airflow]'"
    ) from exc


class DuckCheckOperator(BaseOperator):
    """Run a duckcheck suite YAML as an Airflow task.

    On failure (any check fails), raises ``AirflowException`` when
    ``fail_on_error`` is true (default). Pushes a summary dict to XCom key
    ``duckcheck_summary``.
    """

    template_fields = ("suite_path", "source", "source_table", "junit_output")

    def __init__(
        self,
        *,
        suite_path: str,
        source: str | None = None,
        source_table: str | None = None,
        junit_output: str | None = None,
        fail_on_error: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.suite_path = suite_path
        self.source = source
        self.source_table = source_table
        self.junit_output = junit_output
        self.fail_on_error = fail_on_error

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        summary = execute_suite_path(
            self.suite_path,
            source=self.source,
            source_table=self.source_table,
            junit_output=self.junit_output,
        )
        ti = context.get("ti")
        if ti is not None:
            ti.xcom_push(key="duckcheck_summary", value=summary)
        if self.fail_on_error and not summary["passed"]:
            raise AirflowException(
                f"duckcheck suite {summary['suite']!r} failed: "
                f"{summary['failed_count']} check(s) failed"
            )
        return summary

"""Execute data quality checks via DuckDB."""

from dataclasses import dataclass

import duckdb
import structlog

from duckcheck.spec import CheckSpec, SuiteSpec

log = structlog.get_logger()


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    rows_failed: int = 0


@dataclass
class RunReport:
    suite: str
    results: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)


def run_suite(suite: SuiteSpec) -> RunReport:
    conn = duckdb.connect()
    _register_source(conn, suite.source)
    results: list[CheckResult] = []
    for check in suite.checks:
        results.append(_run_check(conn, check))
    conn.close()
    return RunReport(suite=suite.name, results=results)


def _register_source(conn: duckdb.DuckDBPyConnection, source: str) -> None:
    if source.endswith(".csv"):
        conn.execute(
            f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM read_csv_auto('{source}')"
        )
    elif source.endswith(".parquet"):
        conn.execute(
            f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM read_parquet('{source}')"
        )
    else:
        raise ValueError(f"Unsupported source format: {source}")


def _run_check(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    log.info("running_check", name=check.name, type=check.type)
    if check.type == "not_null":
        return _check_not_null(conn, check)
    if check.type == "unique":
        return _check_unique(conn, check)
    if check.type == "accepted_values":
        return _check_accepted_values(conn, check)
    return CheckResult(check.name, False, f"Unknown check type: {check.type}")


def _check_not_null(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = check.column or ""
    sql = f"SELECT COUNT(*) FROM source_data WHERE {col} IS NULL"
    count = conn.execute(sql).fetchone()[0]
    passed = count == 0
    return CheckResult(
        check.name,
        passed,
        f"{count} null values in {col}" if not passed else f"{col} has no nulls",
        rows_failed=count,
    )


def _check_unique(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = check.column or ""
    sql = f"""
        SELECT COUNT(*) - COUNT(DISTINCT {col}) FROM source_data
    """
    dupes = conn.execute(sql).fetchone()[0]
    passed = dupes == 0
    return CheckResult(
        check.name,
        passed,
        f"{dupes} duplicate values in {col}" if not passed else f"{col} is unique",
        rows_failed=dupes,
    )


def _check_accepted_values(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = check.column or ""
    allowed = ", ".join(f"'{v}'" for v in check.values)
    sql = f"SELECT COUNT(*) FROM source_data WHERE {col} NOT IN ({allowed})"
    bad = conn.execute(sql).fetchone()[0]
    passed = bad == 0
    return CheckResult(
        check.name,
        passed,
        f"{bad} rows with invalid {col}" if not passed else f"{col} values accepted",
        rows_failed=bad,
    )

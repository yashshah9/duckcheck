"""Execute data quality checks via DuckDB."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

import duckdb
import structlog

from duckcheck.baseline import BaselineStore
from duckcheck.spec import CheckSpec, SuiteSpec

log = structlog.get_logger()

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
AGE = re.compile(r"^(\d+)([smhd])$")


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


def _ident(name: str) -> str:
    if not IDENT.match(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def _substitute_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), "")

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, value)


def run_suite(suite: SuiteSpec, suite_dir: Path | None = None) -> RunReport:
    conn = duckdb.connect()
    source = _substitute_env(suite.source)
    _register_source(conn, source, suite.source_table, suite_dir)
    baseline = _open_baseline(suite, suite_dir)
    results: list[CheckResult] = []
    for check in suite.checks:
        results.append(_run_check(conn, check, baseline))
    conn.close()
    if baseline is not None:
        baseline.close()
    return RunReport(suite=suite.name, results=results)


def update_baseline(suite: SuiteSpec, suite_dir: Path | None = None) -> Path:
    """Persist current row counts for row_count_delta checks."""
    conn = duckdb.connect()
    source = _substitute_env(suite.source)
    _register_source(conn, source, suite.source_table, suite_dir)
    path = _baseline_path(suite, suite_dir)
    store = BaselineStore(path)
    count = conn.execute("SELECT COUNT(*) FROM source_data").fetchone()[0]
    for check in suite.checks:
        if check.type == "row_count_delta":
            store.set(check.name, int(count))
    store.close()
    conn.close()
    return path


def _register_source(
    conn: duckdb.DuckDBPyConnection,
    source: str,
    source_table: str | None,
    suite_dir: Path | None,
) -> None:
    if source.startswith("postgres://") or source.startswith("postgresql://"):
        conn.execute("INSTALL postgres; LOAD postgres;")
        conn.execute(f"ATTACH '{source}' AS remote (TYPE POSTGRES)")
        table = _ident(source_table or "public.orders".split(".")[-1])
        conn.execute(f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM remote.{table}")
        return
    if source.startswith("mysql://"):
        conn.execute("INSTALL mysql; LOAD mysql;")
        conn.execute(f"ATTACH '{source}' AS remote (TYPE MYSQL)")
        table = _ident(source_table or "orders")
        conn.execute(f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM remote.{table}")
        return
    if source.startswith("sqlite://") or source.endswith(".db") or source.endswith(".sqlite"):
        db_path = source.removeprefix("sqlite://")
        path = _resolve_file_source(db_path, suite_dir)
        table = _ident(source_table or "source_data")
        conn.execute(f"ATTACH '{path}' AS remote (TYPE SQLITE)")
        conn.execute(f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM remote.{table}")
        return

    path = _resolve_file_source(source, suite_dir)
    resolved = str(path)
    if resolved.endswith(".csv"):
        conn.execute(
            f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM read_csv_auto('{resolved}')"
        )
    elif resolved.endswith(".parquet"):
        conn.execute(
            f"CREATE OR REPLACE VIEW source_data AS SELECT * FROM read_parquet('{resolved}')"
        )
    else:
        raise ValueError(f"Unsupported source format: {source}")


def _resolve_file_source(source: str, suite_dir: Path | None) -> Path:
    path = Path(source)
    if path.is_absolute():
        return path
    candidates: list[Path] = []
    if suite_dir is not None:
        candidates.append(suite_dir / path)
        candidates.append(suite_dir / path.name)
    candidates.append(Path.cwd() / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _baseline_path(suite: SuiteSpec, suite_dir: Path | None) -> Path:
    raw = suite.baseline or ".duckcheck/baseline.db"
    path = Path(raw)
    if path.is_absolute():
        return path
    root = suite_dir or Path.cwd()
    return root / path


def _open_baseline(suite: SuiteSpec, suite_dir: Path | None) -> BaselineStore | None:
    if not any(c.type == "row_count_delta" for c in suite.checks):
        return None
    return BaselineStore(_baseline_path(suite, suite_dir))


def _now_sql() -> str:
    raw = os.environ.get("DUCKCHECK_NOW")
    if raw:
        return f"TIMESTAMP '{raw}'"
    return "now()"


def _run_check(
    conn: duckdb.DuckDBPyConnection,
    check: CheckSpec,
    baseline: BaselineStore | None = None,
) -> CheckResult:
    log.info("running_check", name=check.name, type=check.type)
    dispatch = {
        "not_null": _check_not_null,
        "unique": _check_unique,
        "accepted_values": _check_accepted_values,
        "custom_sql": _check_custom_sql,
        "freshness": _check_freshness,
        "row_count": _check_row_count,
        "row_count_delta": lambda c, spec: _check_row_count_delta(c, spec, baseline),
    }
    handler = dispatch.get(check.type)
    if handler is None:
        return CheckResult(check.name, False, f"Unknown check type: {check.type}")
    return handler(conn, check)


def _check_not_null(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = _ident(check.column or "")
    count = conn.execute(f"SELECT COUNT(*) FROM source_data WHERE {col} IS NULL").fetchone()[0]
    passed = count == 0
    return CheckResult(
        check.name,
        passed,
        f"{count} null values in {col}" if not passed else f"{col} has no nulls",
        rows_failed=count,
    )


def _check_unique(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = _ident(check.column or "")
    dupes = conn.execute(
        f"SELECT COUNT(*) - COUNT(DISTINCT {col}) FROM source_data"
    ).fetchone()[0]
    passed = dupes == 0
    return CheckResult(
        check.name,
        passed,
        f"{dupes} duplicate values in {col}" if not passed else f"{col} is unique",
        rows_failed=dupes,
    )


def _check_accepted_values(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = _ident(check.column or "")
    allowed = ", ".join(f"'{v}'" for v in check.values)
    bad = conn.execute(
        f"SELECT COUNT(*) FROM source_data WHERE {col} NOT IN ({allowed})"
    ).fetchone()[0]
    passed = bad == 0
    return CheckResult(
        check.name,
        passed,
        f"{bad} rows with invalid {col}" if not passed else f"{col} values accepted",
        rows_failed=bad,
    )


def _check_custom_sql(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    sql = (check.sql or "").strip()
    if not sql.lower().startswith("select"):
        return CheckResult(check.name, False, "custom_sql must be a SELECT statement.")
    rows = conn.execute(sql).fetchall()
    failed = len(rows)
    passed = failed == 0
    return CheckResult(
        check.name,
        passed,
        "custom SQL returned 0 failing rows" if passed else f"{failed} failing rows",
        rows_failed=failed,
    )


def _parse_age(spec: str) -> str:
    match = AGE.match(spec)
    if not match:
        raise ValueError(f"Invalid max_age '{spec}'. Use Ns/Nm/Nh/Nd.")
    value, unit = match.groups()
    mapping = {"s": "SECOND", "m": "MINUTE", "h": "HOUR", "d": "DAY"}
    return f"INTERVAL {int(value)} {mapping[unit]}"


def _check_freshness(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    col = _ident(check.column or "")
    interval = _parse_age(check.max_age or "24h")
    stale = conn.execute(
        f"SELECT COUNT(*) FROM source_data WHERE {col} < {_now_sql()} - {interval}"
    ).fetchone()[0]
    passed = stale == 0
    return CheckResult(
        check.name,
        passed,
        f"{stale} stale rows in {col}" if not passed else f"{col} is fresh",
        rows_failed=stale,
    )


def _check_row_count(conn: duckdb.DuckDBPyConnection, check: CheckSpec) -> CheckResult:
    count = conn.execute("SELECT COUNT(*) FROM source_data").fetchone()[0]
    too_few = check.min_rows is not None and count < check.min_rows
    too_many = check.max_rows is not None and count > check.max_rows
    passed = not too_few and not too_many
    return CheckResult(
        check.name,
        passed,
        f"row count {count} outside [{check.min_rows}, {check.max_rows}]"
        if not passed
        else f"row count {count} within bounds",
        rows_failed=0 if passed else 1,
    )


def _check_row_count_delta(
    conn: duckdb.DuckDBPyConnection,
    check: CheckSpec,
    baseline: BaselineStore | None,
) -> CheckResult:
    count = int(conn.execute("SELECT COUNT(*) FROM source_data").fetchone()[0])
    if baseline is None:
        return CheckResult(check.name, False, "row_count_delta requires a baseline store")
    previous = baseline.get(check.name)
    if previous is None:
        return CheckResult(
            check.name,
            False,
            f"no baseline for {check.name}; run duckcheck baseline update",
        )
    if previous == 0:
        drift = 0.0 if count == 0 else 100.0
    else:
        drift = abs(count - previous) / previous * 100.0
    tol = check.tolerance_pct if check.tolerance_pct is not None else 10.0
    passed = drift <= tol
    return CheckResult(
        check.name,
        passed,
        f"row count {count} vs baseline {previous} ({drift:.1f}% drift, tol {tol}%)"
        if not passed
        else f"row count {count} within {tol}% of baseline {previous}",
        rows_failed=0 if passed else 1,
    )


def to_junit(report: RunReport) -> str:
    """Serialize results as JUnit XML for CI dashboards."""
    suite = Element("testsuite", name=report.suite, tests=str(len(report.results)))
    failures = 0
    for result in report.results:
        case = SubElement(suite, "testcase", name=result.name, classname=report.suite)
        if not result.passed:
            failures += 1
            failure = SubElement(case, "failure", message=result.message)
            failure.text = result.message
    suite.set("failures", str(failures))
    return tostring(suite, encoding="unicode")

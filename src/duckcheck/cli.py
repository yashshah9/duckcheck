"""CLI for duckcheck."""

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from duckcheck import __version__
from duckcheck.runner import run_suite, to_junit, update_baseline
from duckcheck.spec import SuiteSpec

console = Console()


@click.group()
@click.version_option(__version__)
def main() -> None:
    """Lightweight data quality checks powered by DuckDB."""


@main.command("health")
def health() -> None:
    console.print(f"[green]duckcheck {__version__} OK[/green]")


@main.command("run")
@click.argument("suite_path", type=click.Path(exists=True, path_type=Path))
@click.option("--junit", type=click.Path(path_type=Path), default=None)
@click.option("--source-table", default=None, help="Override attached SQL table name")
def run_cmd(suite_path: Path, junit: Path | None, source_table: str | None) -> None:
    raw = yaml.safe_load(suite_path.read_text())
    suite = SuiteSpec.model_validate(raw)
    if source_table:
        suite.source_table = source_table
    report = run_suite(suite, suite_dir=suite_path.parent)

    table = Table(title=f"Results: {report.suite}")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for r in report.results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(r.name, status, r.message)
    console.print(table)

    if junit:
        junit.write_text(to_junit(report), encoding="utf-8")
        console.print(f"Wrote JUnit report to {junit}")

    if not report.passed:
        sys.exit(1)


@main.command("baseline")
@click.argument("action", type=click.Choice(["update"]))
@click.argument("suite_path", type=click.Path(exists=True, path_type=Path))
def baseline_cmd(action: str, suite_path: Path) -> None:
    """Persist current row counts for row_count_delta checks."""
    raw = yaml.safe_load(suite_path.read_text())
    suite = SuiteSpec.model_validate(raw)
    path = update_baseline(suite, suite_dir=suite_path.parent)
    console.print(f"[green]Updated baseline[/green] {path}")


if __name__ == "__main__":
    main()

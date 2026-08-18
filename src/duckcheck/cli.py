"""CLI for duckcheck."""

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from duckcheck import __version__
from duckcheck.runner import run_suite
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
def run_cmd(suite_path: Path) -> None:
    raw = yaml.safe_load(suite_path.read_text())
    suite = SuiteSpec.model_validate(raw)
    report = run_suite(suite)

    table = Table(title=f"Results: {report.suite}")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for r in report.results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(r.name, status, r.message)
    console.print(table)

    if not report.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

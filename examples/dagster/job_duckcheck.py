"""Minimal Dagster job using duckcheck_op.

Requires: pip install 'duckcheck[dagster]'
"""

from pathlib import Path

from dagster import Definitions, job

from duckcheck.dagster_op import duckcheck_op

ROOT = Path(__file__).resolve().parents[2]
SUITE = str(ROOT / "examples" / "clean.yaml")

validate = duckcheck_op(name="validate_clean_fixture", suite_path=SUITE)


@job
def duckcheck_example_job():
    validate()


defs = Definitions(jobs=[duckcheck_example_job])

"""Minimal Airflow DAG using DuckCheckOperator.

Requires: pip install 'duckcheck[airflow]'
Point suite_path at a real checks YAML (examples/clean.yaml in this repo).
"""

from datetime import datetime
from pathlib import Path

from airflow import DAG

from duckcheck.airflow_op import DuckCheckOperator

ROOT = Path(__file__).resolve().parents[2]
SUITE = str(ROOT / "examples" / "clean.yaml")

with DAG(
    dag_id="duckcheck_example",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["duckcheck"],
) as dag:
    DuckCheckOperator(
        task_id="validate_clean_fixture",
        suite_path=SUITE,
        fail_on_error=True,
    )

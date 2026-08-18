"""Tests for duckcheck runner."""

from pathlib import Path

import yaml

from duckcheck.runner import run_suite
from duckcheck.spec import SuiteSpec

ROOT = Path(__file__).parent.parent
EXAMPLE = ROOT / "examples" / "checks.yaml"


def test_sample_suite_fails_on_null_name() -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    suite = SuiteSpec.model_validate(raw)
    report = run_suite(suite)
    assert not report.passed
    failed = [r for r in report.results if not r.passed]
    assert any(r.name == "name_not_null" for r in failed)

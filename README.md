# duckcheck

Lightweight data quality checks powered by **DuckDB** — the anti–Great Expectations for teams who want `pip install`, one YAML file, and one command.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/yashshah9/duckcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/yashshah9/duckcheck/actions/workflows/ci.yml)

> **Status:** v0.5 — CSV/Parquet/SQLite sources, custom SQL with field substitution + `expect`, pattern regex, freshness, baselines, JUnit, and `--format json`.

## 60-second try

```bash
docker compose run --rm run-example  # duckcheck run examples/clean.yaml
docker compose run --rm test         # pytest
```

## Why this vs alternatives

| Approach | Strength | Gap |
|----------|----------|-----|
| **duckcheck** | One YAML + DuckDB, local files, CI-friendly | Not a full observability platform |
| Great Expectations | Rich ecosystem | Heavyweight setup for simple column checks |
| Soda Core | Familiar check DSL | Cloud-oriented workflow |
| Ad-hoc SQL in CI | Zero new tools | No standard report / JUnit / baselines |

## Problem

Data teams need to assert column quality in CI, but Great Expectations is heavyweight and Soda Core funnels to cloud. Ad-hoc SQL checks have no reporting standard.

## Key features (v0.5)

- YAML check definitions
- DuckDB scans CSV, Parquet, and SQLite locally — no server
- Checks: `not_null`, `unique`, `accepted_values`, `custom_sql`, `pattern`, `freshness`, `row_count`, `row_count_delta`
- `custom_sql` `${column}` / `${name}` substitution; `expect` operators: `0`, `=N`, `>N`, `<N`, `>=N`, `<=N` (default `0`)
- `--format json` and `--junit` for CI dashboards
- `${ENV}` in source URIs; `--source-table` for SQL ATTACH

## Architecture

```
duckcheck run checks.yaml
    └── SuiteSpec (Pydantic)
            └── DuckDB in-process
                    └── source_data view from CSV/Parquet
```

| Component | Technology | Why |
|-----------|------------|-----|
| Engine | DuckDB | Single dependency, scans files + SQL databases |
| CLI | Click + Rich | Simple, good terminal UX |
| Spec | YAML + Pydantic | Version-controllable checks |

## Installation

```bash
pip install duckcheck
pip install -e ".[dev]"
```

## Usage

```bash
duckcheck health
duckcheck run examples/clean.yaml
duckcheck run examples/checks.yaml   # fixture with known failures
duckcheck run examples/clean.yaml --junit /tmp/duckcheck.xml
duckcheck run examples/clean.yaml --format json
duckcheck baseline update examples/clean.yaml
```

Example `checks.yaml`:

```yaml
name: sample-suite
source: examples/sample.csv
checks:
  - name: id_not_null
    type: not_null
    column: id
  - name: status_values
    type: accepted_values
    column: status
    values: [active, inactive]
  - name: three_active
    type: custom_sql
    sql: "SELECT * FROM source_data WHERE status = 'active'"
    expect: "=3"
```

## Docker

```bash
docker compose run --rm test
docker compose run --rm run-example
```

## Running tests

```bash
pytest tests/ -v
```

## Roadmap

- [x] Freshness + row_count + custom_sql + JUnit
- [x] Row-count baseline delta store (`duckcheck baseline update`)
- [x] custom_sql `expect` operators + `--format json`
- [x] custom_sql `${column}` / `${name}` substitution + `pattern` checks
- [ ] Live Postgres/MySQL ATTACH integration tests
- [ ] Airflow/Dagster operators

## License

MIT

## Known limitations (v0.5)

- Postgres/MySQL ATTACH is stubbed (`INSTALL/LOAD`) — no live DB in CI yet
- `examples/checks.yaml` is a failing fixture; `examples/clean.yaml` is the happy path
- Checks still run against a `source_data` view

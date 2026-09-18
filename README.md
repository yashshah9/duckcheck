# duckcheck

Lightweight data quality checks powered by **DuckDB** — the anti–Great Expectations for teams who want `pip install`, one YAML file, and one command.

[![PyPI](https://img.shields.io/pypi/v/duckcheck.svg)](https://pypi.org/project/duckcheck/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/yashshah9/duckcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/yashshah9/duckcheck/actions/workflows/ci.yml)

> **Status:** v0.7 — CSV/Parquet/SQLite/**Postgres/MySQL** sources, custom SQL + `expect`, pattern, freshness, baselines, JUnit, `--format json`.

## 60-second try

```bash
pip install duckcheck
duckcheck run examples/clean.yaml
# or with Docker:
docker compose run --rm run-example
# live Postgres / MySQL ATTACH examples:
docker compose run --rm run-postgres-example
docker compose run --rm run-mysql-example
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

## Key features (v0.7)

- YAML check definitions
- DuckDB scans CSV, Parquet, SQLite, Postgres, and MySQL (ATTACH) — no separate DQ server
- Checks: `not_null`, `unique`, `accepted_values`, `custom_sql`, `pattern`, `freshness`, `row_count`, `row_count_delta`
- `custom_sql` `${column}` / `${name}` substitution; `expect` operators: `0`, `=N`, `>N`, `<N`, `>=N`, `<=N` (default `0`)
- `--format json` and `--junit` for CI dashboards
- `${ENV}` in source URIs; `--source-table` for SQL ATTACH

## Architecture

```
duckcheck run checks.yaml
    └── SuiteSpec (Pydantic)
            └── DuckDB in-process
                    └── source_data view from CSV/Parquet/SQLite/Postgres/MySQL
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

Postgres (compose hostname `postgres`; from the host set `DUCKCHECK_PG_DSN`):

```yaml
name: postgres-suite
source: postgresql://duckcheck:duckcheck@postgres:5432/duckcheck
source_table: orders
```

MySQL (compose hostname `mysql`; from the host set `DUCKCHECK_MYSQL_DSN`):

```yaml
name: mysql-suite
source: mysql://duckcheck:duckcheck@mysql:3306/duckcheck
source_table: orders
```

## Docker

```bash
docker compose run --rm test
docker compose run --rm run-example
docker compose run --rm run-postgres-example
docker compose run --rm run-mysql-example
```

## Running tests

```bash
pytest tests/ -v
# live Postgres ATTACH (after compose postgres is up):
# compose publishes Postgres on host port 5433
DUCKCHECK_PG_DSN=postgresql://duckcheck:duckcheck@localhost:5433/duckcheck \
  pytest tests/test_runner.py::test_postgres_attach_live -v
# live MySQL ATTACH (compose publishes MySQL on host port 3307):
DUCKCHECK_MYSQL_DSN=mysql://duckcheck:duckcheck@127.0.0.1:3307/duckcheck \
  pytest tests/test_runner.py::test_mysql_attach_live -v
```

## Roadmap

- [x] Freshness + row_count + custom_sql + JUnit
- [x] Row-count baseline delta store (`duckcheck baseline update`)
- [x] custom_sql `expect` operators + `--format json`
- [x] custom_sql `${column}` / `${name}` substitution + `pattern` checks
- [x] Live Postgres ATTACH (compose example + optional `DUCKCHECK_PG_DSN` test)
- [x] Live MySQL ATTACH (compose example + optional `DUCKCHECK_MYSQL_DSN` test)
- [ ] Airflow/Dagster operators

## License

MIT

## Known limitations (v0.7)

- Airflow/Dagster operators not shipped yet
- `examples/checks.yaml` is a failing fixture; `examples/clean.yaml` / `examples/postgres.yaml` / `examples/mysql.yaml` are happy paths
- Checks still run against a `source_data` view

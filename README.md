# duckcheck

Lightweight data quality checks powered by **DuckDB** — the anti–Great Expectations for teams who want `pip install`, one YAML file, and one command.

> **Status:** v0.3 — CSV/Parquet/SQLite sources, custom SQL, freshness, row_count_delta baselines, and JUnit.

## Problem

Data teams need to assert column quality in CI, but Great Expectations is heavyweight and Soda Core funnels to cloud. Ad-hoc SQL checks have no reporting standard.

## Key features (v0.2)

- YAML check definitions
- DuckDB scans CSV, Parquet, and SQLite locally — no server
- Checks: `not_null`, `unique`, `accepted_values`, `custom_sql`, `freshness`, `row_count`, `row_count_delta`
- `--junit` for CI dashboards
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
- [ ] Live Postgres/MySQL ATTACH integration tests
- [ ] Airflow/Dagster operators

## License

MIT

## Known limitations (v0.3)

- Postgres/MySQL ATTACH is stubbed (`INSTALL/LOAD`) — no live DB in CI yet
- `examples/checks.yaml` is a failing fixture; `examples/clean.yaml` is the happy path
- Checks still run against a `source_data` view

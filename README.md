# duckcheck

Lightweight data quality checks powered by **DuckDB** — the anti–Great Expectations for teams who want `pip install`, one YAML file, and one command.

> **Status:** v0.1 foundation — not_null, unique, accepted_values checks on CSV/Parquet; Postgres attach and JUnit output are next.

## Problem

Data teams need to assert column quality in CI, but Great Expectations is heavyweight and Soda Core funnels to cloud. Ad-hoc SQL checks have no reporting standard.

## Key features (v0.1)

- YAML check definitions
- DuckDB scans CSV and Parquet locally — no server
- Checks: `not_null`, `unique`, `accepted_values`
- CLI with pass/fail exit codes for CI
- Rich terminal output

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
duckcheck run examples/checks.yaml
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

- [ ] Postgres/MySQL via DuckDB ATTACH
- [ ] Row count delta / freshness checks
- [ ] JUnit XML output for CI
- [ ] Custom SQL checks

## License

MIT

## Known limitations (v0.1)

- CSV and Parquet sources only
- Checks reference `source_data` view implicitly
- No baseline/drift mode yet
- No Airflow/Dagster operators yet

# Changelog

## [0.7.0] - 2026-09-18

### Added
- Live MySQL ATTACH path (compose `mysql` + `examples/mysql.yaml` + `run-mysql-example`)
- Optional integration test gated by `DUCKCHECK_MYSQL_DSN`

### Fixed
- Materialize ATTACH sources into a local `source_data` table so MySQL row_count / aggregates work

## [0.6.0] - 2026-09-14

### Added
- Live Postgres ATTACH path with clear errors on connect/table failures
- Compose `postgres` service (postgres:16-alpine) + seed `orders` table
- `examples/postgres.yaml` and `run-postgres-example` compose service
- Optional integration test gated by `DUCKCHECK_PG_DSN`

## [0.5.0] - 2026-09-14

### Added
- `custom_sql` `${column}` / `${name}` substitution from check config fields
- `pattern` check type — regex match on non-null column values

## [0.4.0] - 2026-09-14

### Added
- `custom_sql` `expect` operators: `0`, `=N`, `>N`, `<N`, `>=N`, `<=N` (default `0`)
- `duckcheck run --format json` for machine-readable CI output

## [0.3.0] - 2026-08-19

### Added
- SQLite sources (`sqlite://path` or `.db`) via DuckDB ATTACH
- `row_count_delta` checks with `duckcheck baseline update`
- `DUCKCHECK_NOW` to freeze freshness comparisons in tests/CI

## [0.2.0] - 2026-08-19

### Added
- Check types: `custom_sql`, `freshness`, `row_count`
- `--junit` XML output and `--source-table` override
- `${ENV}` substitution in source URIs; suite-relative CSV/Parquet paths
- Postgres/MySQL ATTACH stubs (not integration-tested against a live DB)

## [0.1.0] - 2026-08-18

### Added
- DuckDB-powered not_null, unique, accepted_values checks
- YAML suite format and CLI

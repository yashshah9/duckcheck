# Changelog

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

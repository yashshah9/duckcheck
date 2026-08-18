# Changelog

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

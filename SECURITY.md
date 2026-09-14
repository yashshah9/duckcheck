# Security Policy

## Reporting a vulnerability

Email **yash376351@gmail.com** with the repo name, a short description, and steps to reproduce. Please do not open a public issue for exploitable findings until we have had a reasonable chance to respond.

## Threat model (honest)

duckcheck runs SQL checks locally via DuckDB against files or attached databases you point it at.

- Custom SQL is executed as written — only load suites and sources you trust.
- `${ENV}` substitution can pull secrets into URIs; prefer non-secret paths in committed YAML.
- duckcheck is a **data quality runner**, not an access-control layer for your warehouse.
- Postgres/MySQL ATTACH helpers are stubs today; do not assume network DB hardening from this tool.

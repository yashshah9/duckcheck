# Contributing

## Running tests

Prefer Docker Compose:

```bash
docker compose run --rm test
docker compose run --rm run-example
```

Locally:

```bash
pip install -e ".[dev]"
pytest tests/ -v
duckcheck run examples/clean.yaml
```

## Pull requests

- Keep example suites intentional (`clean.yaml` passes; `checks.yaml` may fail on purpose)
- Update README/CHANGELOG for new check types or CLI flags
- Prefer small PRs with a clear test plan

## Commit style

- Imperative subject line; mention the user-facing why when relevant
- Do not add AI co-author trailers (e.g. Co-authored-by: Cursor) to commits.

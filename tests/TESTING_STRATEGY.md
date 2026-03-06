# Testing Strategy

This project uses a layered test strategy so "tests pass" is a stronger signal for production readiness.

## Layers

- `unit`: deterministic local logic tests.
- `integration`: multi-module workflow tests with external boundaries mocked.
- `e2e`: real external dependency checks (network/system).

## Default Gate

Default `pytest` execution excludes `e2e` tests:

```bash
uv run pytest
```

This validates deterministic behavior and production contracts without internet/system flakiness.

## Full Validation

Run all layers (including real external tests):

```bash
uv run pytest -o addopts="--strict-markers"
```

Or run only real external smoke checks:

```bash
uv run pytest -m e2e -o addopts="--strict-markers"
```

## Why this helps

- Fast failures for regressions in core logic and orchestration contracts.
- Real external smoke tests remain available to detect drift in upstream services.
- Clear separation prevents flaky external dependencies from masking local regressions.

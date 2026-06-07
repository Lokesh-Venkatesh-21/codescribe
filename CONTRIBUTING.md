# Contributing To CodeScribe

Thanks for helping make CodeScribe better. This project is intended to be a safe, useful GitHub
Action that other teams can adopt without handing over source code to paid hosted LLMs by default.

## Local Setup

```bash
cp .env.example .env
make install
make test
make lint
```

## Development Guidelines

- Keep GitHub publishing opt-in and safe by default.
- Do not add network-dependent tests unless they are explicitly skipped or mocked.
- Keep provider integrations behind service adapters.
- Add focused tests for new behavior.
- Update README and action inputs when user-facing behavior changes.
- Do not commit `.env`, tokens, local databases, logs, model files, generated reports, or local
  smoke-test outputs.

## Pull Request Checklist

- `python3 -m pytest` passes.
- `python3 -m ruff check .` passes.
- New public behavior is documented.
- No secrets or generated local artifacts are committed.
- Risky publishing behavior remains disabled unless the adopter explicitly enables it.

## Release Notes

For Marketplace releases, update the version tag used by adopters:

```bash
git tag v0.1.0
git push origin v0.1.0
git tag -f v1 v0.1.0
git push origin v1 --force
```

Use semantic version tags for immutable releases and keep `v1` as the stable major-version pointer.

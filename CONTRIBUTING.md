# Contributing

Thanks for helping improve CodeScribe.

## Local Setup

```bash
cp .env.example .env
make install
make test
make lint
```

## Development Guidelines

- Keep external systems behind service adapters.
- Add tests for new behavior.
- Do not commit `.env`, tokens, local databases, generated datasets, or model files.
- Prefer deterministic tests over network calls.
- Keep GitHub publishing opt-in and safe by default.

## Pull Request Checklist

- `python3 -m pytest` passes.
- `python3 -m ruff check .` passes.
- Public docs are updated for user-facing changes.
- No secrets or generated local artifacts are committed.


# CodeScribe

CodeScribe is a local-first AI documentation, PR intelligence, and AI review platform for GitHub
pull requests. It analyzes PR diffs, extracts AST metadata, generates documentation and review
reports, scores risk and quality, stores human feedback, and can optionally publish review comments
back to GitHub.

The default LLM provider is Ollama, so CodeScribe can run without paid API keys. If Ollama is not
available, the system falls back to deterministic local output so workflows still complete.

## Features

- GitHub webhook ingestion for pull request events.
- GitHub Actions mode with `codescribe analyze-pr`.
- Python AST parsing and lightweight Go, Java, and TypeScript symbol detection.
- Ollama-backed documentation generation with optional Gemini support.
- PR intelligence reports: classification, risk, security, quality, impact, and dependencies.
- AI review decisions: `APPROVE`, `REQUEST_CHANGES`, or `NEEDS_HUMAN_REVIEW`.
- Inline review comments with file, line, severity, issue, and suggested improvement.
- Human approval mode before GitHub publishing.
- Human feedback tracking, accuracy metrics, reviewer agreement metrics, and JSONL dataset export.
- Docker Compose stack for FastAPI, PostgreSQL, Redis, and Ollama.

## Architecture

CodeScribe has two operating modes:

- **Webhook server mode**: Run FastAPI as a service. GitHub sends PR webhook events to
  `/api/v1/webhooks/github`.
- **GitHub Actions mode**: Run `codescribe analyze-pr` directly in a PR workflow. No external
  webhook server is required.

Core flow:

1. Receive or extract a PR diff.
2. Detect changed files and languages.
3. Parse symbols and AST metadata.
4. Generate documentation artifacts.
5. Run PR intelligence, risk, security, and quality analysis.
6. Generate AI review comments and a review decision.
7. Store reports, metrics, feedback, and learning data.
8. Optionally publish review comments to GitHub.

See [ARCHITECTURE.md](ARCHITECTURE.md) for more detail.

## Quick Start

```bash
cp .env.example .env
make install
make dev
```

Open:

- Health: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>

Run a sample PR:

```bash
python scripts/smoke_process_pr.py
```

## Ollama Setup

Install and start Ollama:

```bash
brew install ollama
ollama serve
ollama pull qwen3:8b
```

Default Ollama settings:

- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=qwen3:8b`

Docker Compose also includes an Ollama service. To pull the model through Compose:

```bash
docker compose --profile models up ollama-pull
```

## Environment Variables

See [.env.example](.env.example).

Important settings:

- `DATABASE_URL`: async SQLAlchemy database URL.
- `REDIS_URL`: Redis URL.
- `GITHUB_WEBHOOK_SECRET`: shared secret for webhook signature validation.
- `GITHUB_TOKEN`: optional token for fetching PR files and publishing comments.
- `LLM_PROVIDER`: `ollama`, `gemini`, or `local_fallback`.
- `OLLAMA_BASE_URL`: Ollama endpoint.
- `OLLAMA_MODEL`: Ollama model name.
- `LLM_REQUEST_TIMEOUT_SECONDS`: LLM request timeout.
- `LLM_MAX_RETRIES`: LLM retry attempts before fallback.
- `AUTO_POST_REVIEWS`: defaults to `false`.
- `POST_PR_COMMENT`: defaults to `false` for GitHub Actions mode.
- `TRAINING_DATASET_PATH`: JSONL feedback dataset path.

Never commit a real `.env` file or tokens.

## Docker

Run the complete local stack:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- `api`: FastAPI app on port `8000`
- `postgres`: PostgreSQL on port `5432`
- `redis`: Redis on port `6379`
- `ollama`: Ollama on port `11434`

Persistent volumes:

- `postgres_data`
- `ollama_data`

## GitHub Webhook Setup

1. Deploy CodeScribe where GitHub can reach it.
2. Set `GITHUB_WEBHOOK_SECRET` in `.env`.
3. In GitHub, add a repository webhook:
   - Payload URL: `https://your-host/api/v1/webhooks/github`
   - Content type: `application/json`
   - Secret: same value as `GITHUB_WEBHOOK_SECRET`
   - Events: pull request events
4. Optional publishing:
   - Set `GITHUB_TOKEN` with PR read/write permissions.
   - Keep `AUTO_POST_REVIEWS=false` unless you explicitly want automatic review publishing.

Webhook signatures are validated outside local/dev/test environments.

## GitHub Actions Mode

CodeScribe can run without a server:

```yaml
name: CodeScribe
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  codescribe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Lokesh-Venkatesh-21/codescribe@main
        with:
          post-comment: false
          output-dir: codescribe-reports
      - uses: actions/upload-artifact@v4
        with:
          name: codescribe-reports
          path: codescribe-reports
```

Safe defaults:

- PR comments are disabled unless `post-comment: true`.
- Reviews are not auto-approved.
- Requesting changes is not automatically posted unless publishing is explicitly enabled.
- Reports are always generated.

## CLI

```bash
codescribe analyze-pr \
  --repo acme/widgets \
  --pr-number 42 \
  --base-ref origin/main \
  --head-ref HEAD \
  --output-dir codescribe-reports \
  --post-comment false
```

Generated reports:

- `documentation_report.md`
- `pr_summary.md`
- `risk_report.md`
- `security_report.md`
- `impact_analysis.md`
- `quality_report.md`
- `review_report.md`

## API Examples

Process a local PR payload:

```bash
curl -X POST http://localhost:8000/api/v1/pull-requests/process \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "acme/widgets",
    "pr_number": 42,
    "head_sha": "abc123",
    "title": "Add widget pricing service",
    "author": "octocat",
    "files": [
      {
        "filename": "app/pricing.py",
        "status": "added",
        "patch": "@@\n+class PricingService:\n+    def quote(self, sku, quantity):\n+        return quantity * 10\n",
        "additions": 3,
        "deletions": 0
      }
    ]
  }'
```

Read generated review:

```bash
curl http://localhost:8000/api/v1/pr/{pull_request_id}/review
```

Submit human feedback:

```bash
curl -X POST http://localhost:8000/api/v1/review/{review_id}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "human_reviewer_decision": "NEEDS_HUMAN_REVIEW",
    "outcome": "accepted",
    "reviewer": "docs-lead",
    "team": "platform",
    "notes": "The testing recommendation was useful."
  }'
```

Dashboard metrics:

```bash
curl http://localhost:8000/api/v1/metrics
curl http://localhost:8000/api/v1/metrics/accuracy
curl http://localhost:8000/api/v1/metrics/reviewer-agreement
```

## Demo Workflow

1. Start the API with `make dev` or `docker compose up --build`.
2. Run `python scripts/smoke_process_pr.py`.
3. Open `/api/v1/pr/{id}/review`.
4. Approve or request changes.
5. Submit feedback with `/api/v1/review/{review_id}/feedback`.
6. Inspect `/api/v1/metrics` and `outputs/training_dataset.jsonl`.

## Troubleshooting

- **Ollama is unavailable**: CodeScribe logs a warning and uses deterministic fallback output.
- **Webhook returns 401**: verify `GITHUB_WEBHOOK_SECRET` and GitHub's webhook secret match.
- **No GitHub comments are posted**: set `GITHUB_TOKEN` and opt into posting.
- **GitHub Actions diff is empty**: ensure `actions/checkout` uses `fetch-depth: 0`.
- **Docker model is missing**: run `docker compose --profile models up ollama-pull`.

## Development

```bash
make install
make test
make lint
```

Before pushing:

```bash
python3 -m pytest
python3 -m ruff check .
```

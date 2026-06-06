# CodeScribe Architecture

CodeScribe is organized around small, testable service modules.

## Runtime Modes

- Webhook server mode: FastAPI receives GitHub pull request webhooks.
- GitHub Actions mode: the `codescribe analyze-pr` CLI reads a checked-out repository diff.

## Main Components

- `app/api/routes`: FastAPI endpoints.
- `app/services/github.py`: GitHub API adapter with retries and timeouts.
- `app/services/llm_providers.py`: Ollama, Gemini, and deterministic fallback providers.
- `app/services/generators.py`: documentation generation.
- `app/services/pr_intelligence.py`: classification, risk, security, dependency, and quality analysis.
- `app/services/review_agent.py`: AI review decision and inline comment generation.
- `app/services/feedback_evaluation.py`: human feedback metrics and dataset export.
- `app/workflows/documentation_graph.py`: end-to-end PR processing workflow.
- `app/cli.py`: serverless GitHub Actions analysis path.

## Data Storage

PostgreSQL stores PR metadata, changed files, generated artifacts, validation results, review
comments, feedback, and metrics. Local development defaults to SQLite when `DATABASE_URL` is not
provided.

## Security Posture

- Webhook signatures are checked outside local/test environments.
- Secrets are loaded from environment variables.
- GitHub comment publishing is opt-in.
- Automatic review posting is disabled by default.
- LLM failures fall back gracefully without dropping PR state.


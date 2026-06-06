# CodeScribe Architecture

CodeScribe turns pull request events into reviewed, validated documentation artifacts.

## Flow

1. GitHub sends a pull request webhook.
2. FastAPI verifies the webhook signature and stores PR metadata.
3. The GitHub adapter fetches changed files and patches.
4. The AST analyzer detects language and extracts functions, classes, imports, and parse errors.
5. The workflow generates module summaries, PR summaries, and release notes.
6. Validation checks AST coverage, documentation completeness, and hallucination risk.
7. Evaluation assigns quality scores and records metrics.
8. Approval records are created for human review.
9. Approved artifacts can be published as GitHub PR comments or through a future docs backend.

## Production Components

- FastAPI API service for webhooks, review, artifacts, and metrics.
- PostgreSQL for PR metadata, artifacts, validations, approvals, feedback, and scores.
- Redis for future durable async worker queues.
- LangGraph topology in `app/workflows/documentation_graph.py` for distributed orchestration.
- Gemini adapter with deterministic local fallback.
- GitHub adapter with retry handling.

## Extension Points

- Replace `PatternParser` with tree-sitter parsers for Go, Java, and TypeScript.
- Move `AsyncTaskQueue` to Arq, Celery, Dramatiq, or Temporal.
- Add LangGraph checkpoints and interrupts for reviewer gates.
- Add publish targets for docs repos, Confluence, Notion, or internal portals.


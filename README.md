# CodeScribe

CodeScribe is a GitHub Actions-first AI pull request reviewer. It starts from
`pull_request` events, analyzes the PR diff, detects changed symbols, scores risk, generates a
review summary, adds optional review comments, and can commit a `documentation.md` audit trail back
to the PR branch.

The GitHub Action is the single workflow entry point.

## What CodeScribe Does

- Reads changed files directly from the checked-out pull request.
- Detects changed Python, Go, Java, and TypeScript symbols.
- Uses AST-aware validation for Python comment-only annotations.
- Generates PR summaries with changed files, changed functions/classes, risk score, and decision.
- Adds optional GitHub PR review comments.
- Updates `documentation.md` for audit and traceability.
- Uses Ollama, optional hosted providers, or deterministic local fallback.
- Keeps risky behavior opt-in: no auto-approval by default, no artifacts by default.

## Architecture Diagrams

The architecture diagrams live in dedicated docs files so they render cleanly on GitHub:

- [High-Level Architecture](docs/diagrams/high-level-architecture.md)
- [PR Processing Flow](docs/diagrams/pr-processing-flow.md)
- [LangGraph Agent Workflow](docs/diagrams/langgraph-agent-workflow.md)
- [Deployment Architecture](docs/diagrams/deployment-architecture.md)
- [LLM Provider Fallback Chain](docs/diagrams/llm-provider-fallback-chain.md)

## Quick Start

Add this workflow to the repository you want CodeScribe to review:

```yaml
name: CodeScribe PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  codescribe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.ref }}

      - uses: Lokesh-Venkatesh-21/codescribe@v1
        with:
          post-comment: true
          post-review: true
          auto-approve: false
          fail-on-risk: false
          risk-threshold: 75
          llm-provider: auto
          write-artifacts: false
          annotate-code: true
          commit-documentation: true
          documentation-file: documentation.md
```

## Safe Defaults

- `post-comment` defaults to `false`.
- `post-review` defaults to `false`.
- `auto-approve` defaults to `false`.
- `write-artifacts` defaults to `false`.
- `annotate-code` defaults to `true`, but executable Python code is AST-validated before writing.
- `commit-documentation` defaults to `true` for the action path.

## Action Inputs

| Input | Default | Purpose |
| --- | --- | --- |
| `post-comment` | `false` | Upsert a sticky PR summary comment. |
| `post-review` | `false` | Publish a GitHub PR review with generated comments. |
| `auto-approve` | `false` | Allow actual `APPROVE` reviews. When false, approvals become `COMMENT`. |
| `fail-on-risk` | `false` | Fail the workflow when risk exceeds `risk-threshold`. |
| `risk-threshold` | `70` | Risk score gate used when `fail-on-risk` is enabled. |
| `llm-provider` | `auto` | `auto`, `ollama`, `gemini`, `generic_api`, `local_model`, or `local_fallback`. |
| `model` | empty | Optional model override. |
| `llm-api-key` | empty | Optional Gemini or OpenAI-compatible provider key. |
| `llm-api-base-url` | empty | Optional OpenAI-compatible API base URL. |
| `include` | empty | Comma-separated glob patterns to include. |
| `exclude` | empty | Comma-separated glob patterns to exclude. |
| `config-file` | `.codescribe.yml` | Optional repository-level CodeScribe config file. |
| `output-dir` | `codescribe-reports` | Directory for optional generated reports. |
| `write-artifacts` | `false` | Write Markdown reports into `output-dir`. |
| `annotate-code` | `true` | Add comment-only annotations above changed Python functions/classes. |
| `commit-documentation` | `true` | Commit annotations and `documentation.md` to the PR branch. |
| `documentation-file` | `documentation.md` | Audit file updated with PR number, date, author, files, symbols, and risk. |

## Output In Pull Requests

CodeScribe can produce:

- A sticky PR summary comment.
- Optional review comments on changed files.
- Optional comment-only annotations in changed Python files.
- A `documentation.md` audit entry committed to the PR branch.

## Optional `.codescribe.yml`

```yaml
risk_threshold: 75
include:
  - "src/**"
  - "app/**"
exclude:
  - "docs/**"
  - "**/generated/**"
review_tone: balanced
review_verbosity: normal
llm_provider: auto
reports:
  - pr_summary
  - risk_report
  - security_report
  - quality_report
  - review_report
```

Action inputs and CLI flags override `.codescribe.yml`.

## LLM Providers

Use `llm-provider: auto` for the safest default. CodeScribe tries available providers in this order:

1. Ollama local endpoint.
2. OpenAI-compatible generic API when configured.
3. Optional local model package.
4. Deterministic local fallback.

For local Ollama:

```bash
brew install ollama
ollama serve
ollama pull qwen3:8b
```

## CLI Usage

The action invokes this same CLI internally:

```bash
codescribe analyze-pr \
  --repo acme/widgets \
  --pr-number 42 \
  --base-ref origin/main \
  --head-ref HEAD \
  --post-comment true \
  --post-review false \
  --auto-approve false \
  --write-artifacts false \
  --annotate-code true \
  --commit-documentation true \
  --documentation-file documentation.md
```

## Local Development

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
cp .env.example .env
python3 -m pytest
python3 -m ruff check .
```

Useful commands:

```bash
make install
make test
make lint
```

## Project Structure

```text
app/
  cli.py                  GitHub Actions entry point
  core/                   Settings and config helpers
  parsers/                AST and pattern parsers
  services/               GitHub, LLM, review, intelligence, feedback services
  workflows/              LangGraph-style processing workflow
docs/diagrams/            GitHub-renderable Mermaid diagrams
scripts/action-entrypoint.sh
action.yml                Marketplace-ready composite action
action-container.yml      Optional container action metadata
Dockerfile.action         Container action image
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

Security reports should follow [SECURITY.md](SECURITY.md).

## License

CodeScribe is released under the MIT License. See [LICENSE](LICENSE).

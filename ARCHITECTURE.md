# CodeScribe Architecture

CodeScribe is now GitHub Actions-first. A repository pull request triggers a workflow, the workflow
checks out the PR branch, and the CodeScribe CLI runs the analysis pipeline directly inside the
runner.

The production workflow runs entirely inside GitHub Actions.

## Runtime Entry Point

- GitHub event: `pull_request` with `opened`, `synchronize`, or `reopened`.
- Workflow: `.github/workflows/codescribe.yml` in the adopting repository.
- Action: `Lokesh-Venkatesh-21/codescribe@v1`.
- CLI: `codescribe analyze-pr`.

## Main Components

- `app/cli.py`: reads the git diff, applies include/exclude filters, invokes the pipeline, and
  publishes enabled PR outputs.
- `app/services/ast_analysis.py`: detects language and extracts symbols.
- `app/services/pr_intelligence.py`: classifies change type, scores risk, scans security patterns,
  and creates quality metrics.
- `app/services/llm_providers.py`: selects Ollama, generic API, local model, or deterministic
  fallback.
- `app/services/review_agent.py`: generates review decision and inline comments.
- `app/services/branch_documentation.py`: applies comment-only annotations and updates
  `documentation.md`.
- `app/services/github.py`: posts sticky PR comments and optional GitHub reviews.
- `app/workflows/documentation_graph.py`: reusable workflow implementation for persisted/local
  processing paths.

## Diagrams

- [High-Level Architecture](docs/diagrams/high-level-architecture.md)
- [PR Processing Flow](docs/diagrams/pr-processing-flow.md)
- [LangGraph Agent Workflow](docs/diagrams/langgraph-agent-workflow.md)
- [Deployment Architecture](docs/diagrams/deployment-architecture.md)
- [LLM Provider Fallback Chain](docs/diagrams/llm-provider-fallback-chain.md)

## Security Posture

- GitHub publishing is opt-in.
- Automatic approval is disabled by default.
- Generated report artifacts are disabled by default.
- Secrets are read from GitHub Actions secrets or environment variables.
- LLM provider selection falls back safely without sending code to an unexpected provider.

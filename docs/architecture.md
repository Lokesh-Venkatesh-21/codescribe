# Architecture

CodeScribe runs as a GitHub Action. Pull request events start the workflow, and the action invokes
the CodeScribe CLI inside the GitHub-hosted runner.

## Flow

1. A contributor opens, updates, or reopens a pull request.
2. GitHub Actions checks out the PR branch with full git history.
3. `codescribe analyze-pr` reads the local git diff.
4. Parsers detect changed files and symbols.
5. The PR intelligence engine classifies the change, scores risk, scans security patterns, and
   builds quality signals.
6. The review agent generates a decision, summary, and optional comments.
7. Enabled outputs are posted to the PR or committed to the PR branch.

## Production Components

- Reusable GitHub Action metadata in `action.yml`.
- Optional container action metadata in `action-container.yml`.
- CLI pipeline in `app/cli.py`.
- Parser, LLM, review, and publishing services under `app/services`.
- Mermaid diagrams in `docs/diagrams`.

## Extension Points

- Add tree-sitter parsers for deeper Go, Java, and TypeScript analysis.
- Add SARIF export for security findings.
- Add a GitHub App authentication path for organization-wide rollout.
- Add confidence calibration from historical human feedback.

# Implementation Plan

## Current Architecture

CodeScribe is implemented as a GitHub Actions-first PR reviewer. The workflow starts from
`pull_request` events and invokes `codescribe analyze-pr` directly inside the runner.

## Completed Foundation

1. Reusable composite action in `action.yml`.
2. CLI pipeline in `app/cli.py`.
3. AST and pattern parsers for changed code.
4. PR intelligence engine for classification, risk, security, and quality.
5. LLM provider abstraction with local-first fallback behavior.
6. Review agent and GitHub publishing adapter.
7. Branch documentation support for comment-only annotations and `documentation.md`.

## Next Improvements

1. Improve changed-symbol precision from diff line ranges.
2. Add tree-sitter parsers for Go, Java, and TypeScript.
3. Add SARIF export for security findings.
4. Add GitHub App authentication for organization-wide installation.
5. Add stronger release automation for Marketplace publishing.
6. Add more historical PR evaluation fixtures.

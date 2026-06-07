# Security Policy

CodeScribe analyzes pull request diffs and can optionally publish comments back to GitHub. Treat it
as automation with repository write access when `contents: write`, `pull-requests: write`, or
`issues: write` permissions are enabled.

## Supported Versions

Security fixes are applied to the `main` branch and the latest `v1` major-version action tag.

## Reporting A Vulnerability

Please open a private security advisory on GitHub, or contact the repository owner directly if
advisories are not available. Do not publish proof-of-concept exploits in public issues.

Include:

- Affected version, commit, or action tag.
- Steps to reproduce.
- Impact and affected permissions.
- Any relevant logs with secrets removed.

## Security Defaults

- PR comments and reviews are opt-in.
- Automatic approval is disabled by default.
- Generated report artifacts are disabled by default in the Marketplace action path.
- The production workflow runs inside GitHub Actions using repository-scoped permissions.
- Secrets are read from environment variables, never from committed config.
- LLM failures fall back to deterministic local output rather than leaking data to an unexpected
  provider.

## Recommended Action Permissions

Use the smallest permissions that match the features you enable:

```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
```

Use `contents: write` only when `commit-documentation: true` is enabled.

For pull requests from forks, prefer the default `pull_request` event. Be careful with
`pull_request_target`; only use it after reviewing GitHub's security guidance and avoiding execution
of untrusted code from the fork.

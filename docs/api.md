# CLI Reference

CodeScribe's production workflow is the GitHub Action. The action invokes the CLI directly inside
the GitHub Actions runner.

## Command

```bash
codescribe analyze-pr \
  --repo acme/widgets \
  --pr-number 42 \
  --base-ref origin/main \
  --head-ref HEAD \
  --output-dir codescribe-reports \
  --post-comment true \
  --post-review false \
  --auto-approve false \
  --fail-on-risk false \
  --risk-threshold 75 \
  --llm-provider auto \
  --write-artifacts false \
  --annotate-code true \
  --commit-documentation true \
  --documentation-file documentation.md
```

## Common Flags

| Flag | Purpose |
| --- | --- |
| `--repo` | Repository name, such as `owner/repo`. |
| `--pr-number` | Pull request number. |
| `--base-ref` | Base commit or ref for the diff. |
| `--head-ref` | Head commit or ref for the diff. |
| `--post-comment` | Post or update the sticky PR summary comment. |
| `--post-review` | Publish a GitHub review with generated comments. |
| `--auto-approve` | Allow actual approval reviews. |
| `--fail-on-risk` | Exit non-zero when risk exceeds the threshold. |
| `--risk-threshold` | Risk score threshold. |
| `--llm-provider` | Provider selection: `auto`, `ollama`, `generic_api`, `local_model`, or `local_fallback`. |
| `--write-artifacts` | Write Markdown reports to disk. Disabled by default in the action. |
| `--annotate-code` | Add AST-validated comment-only code annotations. |
| `--commit-documentation` | Commit annotations and `documentation.md` to the PR branch. |

## Outputs

- Sticky PR summary comment.
- Optional GitHub review comments.
- Optional `documentation.md` audit entry.
- Optional Markdown report files when `--write-artifacts true`.

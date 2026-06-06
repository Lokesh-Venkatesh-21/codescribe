# API Reference

## Health

`GET /health`

Returns service status.

## Manual PR Processing

`POST /api/v1/pull-requests/process`

Processes a local or test PR payload without calling GitHub.

## GitHub Webhook

`POST /api/v1/webhooks/github`

Receives `pull_request` events. In non-local environments, requests must include a valid
`X-Hub-Signature-256` header.

## Artifacts

`GET /api/v1/artifacts?pull_request_id=<id>`

Lists generated documentation artifacts.

`GET /api/v1/artifacts/{artifact_id}`

Reads one artifact.

## Approvals

`POST /api/v1/approvals/{approval_id}/decision`

Body:

```json
{
  "status": "approved",
  "reviewer": "docs-lead",
  "comments": "Looks good"
}
```

## Metrics

`GET /api/v1/metrics/quality`

Returns recent quality metrics.

## PR Intelligence

`GET /api/v1/pr/{id}/summary`

Returns the persisted `pr_summary.md` intelligence report.

`GET /api/v1/pr/{id}/risk`

Returns the persisted `risk_report.md` and risk metrics.

`GET /api/v1/pr/{id}/security`

Returns the persisted `security_report.md` and security score.

`GET /api/v1/pr/{id}/quality`

Returns the persisted `quality_report.md` and documentation, complexity, maintainability,
security, and overall quality scores.

`GET /api/v1/pr/{id}/review`

Returns the AI review decision, confidence score, inline comments, publication status, and
`review_report.md`.

`POST /api/v1/pr/{id}/approve`

Marks the generated review as approved for publication.

`POST /api/v1/pr/{id}/request-changes`

Marks the review as human-requested changes and updates the decision to `REQUEST_CHANGES`.

`POST /api/v1/pr/{id}/publish-review`

Publishes the review to GitHub when approved, or when `AUTO_POST_REVIEWS=true`.

## Review Feedback

`POST /api/v1/review/{review_id}/feedback`

Stores human feedback for an AI review.

Body:

```json
{
  "human_reviewer_decision": "NEEDS_HUMAN_REVIEW",
  "outcome": "accepted",
  "reviewer": "docs-lead",
  "team": "platform",
  "notes": "The testing recommendation was useful."
}
```

`GET /api/v1/metrics`

Returns dashboard-ready review accuracy, acceptance, confidence trends, and team statistics.

`GET /api/v1/metrics/accuracy`

Returns false positive rate, false negative rate, reviewer agreement rate, average confidence,
and feedback volume.

`GET /api/v1/metrics/reviewer-agreement`

Returns reviewer agreement rate and confidence metrics.

CREATE TABLE IF NOT EXISTS pull_requests (
  id UUID PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  pr_number INTEGER NOT NULL,
  head_sha VARCHAR(64) NOT NULL,
  title VARCHAR(500) NOT NULL,
  author VARCHAR(255) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'received',
  raw_payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_pull_requests_repo_pr_head UNIQUE (repo_full_name, pr_number, head_sha)
);

CREATE TABLE IF NOT EXISTS changed_files (
  id UUID PRIMARY KEY,
  pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
  path VARCHAR(1000) NOT NULL,
  language VARCHAR(80) NOT NULL,
  status VARCHAR(40) NOT NULL,
  patch TEXT,
  additions INTEGER NOT NULL DEFAULT 0,
  deletions INTEGER NOT NULL DEFAULT 0,
  ast_metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documentation_artifacts (
  id UUID PRIMARY KEY,
  pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
  artifact_type VARCHAR(80) NOT NULL,
  path VARCHAR(1000),
  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL,
  model VARCHAR(120) NOT NULL,
  prompt_version VARCHAR(80) NOT NULL DEFAULT 'v1',
  quality_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS validation_results (
  id UUID PRIMARY KEY,
  artifact_id UUID NOT NULL REFERENCES documentation_artifacts(id) ON DELETE CASCADE,
  validator VARCHAR(120) NOT NULL,
  passed BOOLEAN NOT NULL,
  score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  details JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approvals (
  id UUID PRIMARY KEY,
  artifact_id UUID NOT NULL REFERENCES documentation_artifacts(id) ON DELETE CASCADE,
  status VARCHAR(40) NOT NULL DEFAULT 'pending',
  reviewer VARCHAR(255),
  comments TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
  id UUID PRIMARY KEY,
  artifact_id UUID NOT NULL REFERENCES documentation_artifacts(id) ON DELETE CASCADE,
  reviewer VARCHAR(255) NOT NULL,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quality_metrics (
  id UUID PRIMARY KEY,
  pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
  name VARCHAR(120) NOT NULL,
  value NUMERIC(8, 3) NOT NULL,
  dimensions JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pull_requests_repo_pr ON pull_requests(repo_full_name, pr_number);
CREATE INDEX IF NOT EXISTS idx_artifacts_pr_type ON documentation_artifacts(pull_request_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_metrics_pr_name ON quality_metrics(pull_request_id, name);

CREATE TABLE IF NOT EXISTS reviews (
  id UUID PRIMARY KEY,
  pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
  decision VARCHAR(40) NOT NULL,
  confidence_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  risk_summary TEXT NOT NULL,
  security_summary TEXT NOT NULL,
  improvement_suggestions JSONB NOT NULL DEFAULT '[]',
  publication_status VARCHAR(40) NOT NULL DEFAULT 'draft',
  github_review_id VARCHAR(120),
  published_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_comments (
  id UUID PRIMARY KEY,
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  path VARCHAR(1000) NOT NULL,
  line INTEGER NOT NULL,
  category VARCHAR(80) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  issue TEXT NOT NULL,
  suggestion TEXT NOT NULL,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  github_comment_id VARCHAR(120),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_feedback (
  id UUID PRIMARY KEY,
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
  ai_recommendation VARCHAR(40) NOT NULL,
  human_reviewer_decision VARCHAR(40) NOT NULL,
  outcome VARCHAR(40) NOT NULL,
  reviewer VARCHAR(255) NOT NULL,
  team VARCHAR(255),
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_metrics (
  id UUID PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  value NUMERIC(8, 3) NOT NULL,
  dimensions JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_pr_status ON reviews(pull_request_id, publication_status);
CREATE INDEX IF NOT EXISTS idx_review_comments_review ON review_comments(review_id);
CREATE INDEX IF NOT EXISTS idx_review_feedback_review ON review_feedback(review_id);
CREATE INDEX IF NOT EXISTS idx_review_metrics_name ON review_metrics(name);

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    login: str


class GitHubRepository(BaseModel):
    full_name: str


class GitHubPullRequest(BaseModel):
    number: int
    title: str
    user: GitHubUser
    head: dict = Field(default_factory=dict)


class PullRequestWebhook(BaseModel):
    action: str
    repository: GitHubRepository
    pull_request: GitHubPullRequest


class WebhookAccepted(BaseModel):
    pull_request_id: str
    status: str

import httpx
import pytest

from app.core.config import Settings
from app.services.github import GitHubClient


class FakeAsyncClient:
    calls: list[tuple[str, dict | None, dict | None]] = []

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, headers: dict | None = None, params: dict | None = None):
        self.calls.append((url, headers, params))
        if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
            return httpx.Response(200, text="diff --git a/app.py b/app.py")

        page = params["page"] if params else 1
        if page == 1:
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": f"file-{index}.py",
                        "status": "modified",
                        "patch": "@@\n+def changed():\n+    pass\n",
                        "additions": 2,
                        "deletions": 0,
                        "sha": f"sha-{index}",
                    }
                    for index in range(100)
                ],
            )
        return httpx.Response(
            200,
            json=[
                {
                    "filename": "last.ts",
                    "status": "added",
                    "patch": "@@\n+function changed() {}\n",
                    "additions": 1,
                    "deletions": 0,
                    "sha": "sha-last",
                }
            ],
        )


@pytest.mark.asyncio
async def test_github_client_paginates_files_and_fetches_diff(monkeypatch) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr("app.services.github.httpx.AsyncClient", FakeAsyncClient)

    settings = Settings(github_token="token", github_api_base_url="https://api.github.test")
    client = GitHubClient(settings)

    files = await client.list_pull_request_files("acme/widgets", 22)
    diff = await client.get_pull_request_diff("acme/widgets", 22)

    assert len(files) == 101
    assert files[0].filename == "file-0.py"
    assert files[-1].filename == "last.ts"
    assert diff == "diff --git a/app.py b/app.py"
    assert FakeAsyncClient.calls[0][2] == {"per_page": 100, "page": 1}
    assert FakeAsyncClient.calls[1][2] == {"per_page": 100, "page": 2}

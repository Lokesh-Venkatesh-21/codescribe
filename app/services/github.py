import logging
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitHubChangedFile:
    filename: str
    status: str
    patch: str | None
    additions: int
    deletions: int
    sha: str | None
    previous_filename: str | None
    blob_url: str | None
    raw_url: str | None
    contents_url: str | None
    raw: dict[str, Any]


class GitHubClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.github_api_base_url.rstrip("/")

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(3))
    async def list_pull_request_files(
        self, repo_full_name: str, pr_number: int
    ) -> list[GitHubChangedFile]:
        if not self.settings.github_token:
            logger.info("GITHUB_TOKEN missing; returning no remote files")
            return []

        files: list[GitHubChangedFile] = []
        async with httpx.AsyncClient(timeout=20) as client:
            page = 1
            while True:
                url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/files"
                response = await client.get(
                    url,
                    headers=self._headers(),
                    params={"per_page": 100, "page": page},
                )

                if response.status_code >= 400:
                    raise ExternalServiceError(
                        "GitHub files API failed with "
                        f"{response.status_code}: {response.text[:300]}"
                    )

                items = response.json()
                files.extend(self._to_changed_file(item) for item in items)
                if len(items) < 100:
                    break
                page += 1

        return files

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(3))
    async def get_pull_request_diff(self, repo_full_name: str, pr_number: int) -> str:
        if not self.settings.github_token:
            logger.info("GITHUB_TOKEN missing; returning empty remote diff")
            return ""

        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                headers=self._headers("application/vnd.github.v3.diff"),
            )

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"GitHub diff API failed with {response.status_code}: {response.text[:300]}"
            )

        return response.text

    async def create_pr_comment(self, repo_full_name: str, pr_number: int, body: str) -> None:
        if not self.settings.github_token:
            logger.info("Dry-run GitHub comment for %s #%s:\n%s", repo_full_name, pr_number, body)
            return

        url = f"{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=self._headers(), json={"body": body})

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"GitHub comment API failed with {response.status_code}: {response.text[:300]}"
            )

    async def create_pull_request_review(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
        event: str,
        comments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.settings.github_token:
            logger.info(
                "Dry-run GitHub review for %s #%s event=%s comments=%s:\n%s",
                repo_full_name,
                pr_number,
                event,
                len(comments),
                body,
            )
            return {"id": "dry-run", "state": event, "comments": comments}

        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/reviews"
        payload = {
            "body": body,
            "event": event,
            "comments": comments,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=self._headers(), json=payload)

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"GitHub review API failed with {response.status_code}: {response.text[:300]}"
            )

        return response.json()

    @staticmethod
    def _to_changed_file(item: dict[str, Any]) -> GitHubChangedFile:
        return GitHubChangedFile(
            filename=item["filename"],
            status=item.get("status", "modified"),
            patch=item.get("patch"),
            additions=item.get("additions", 0),
            deletions=item.get("deletions", 0),
            sha=item.get("sha"),
            previous_filename=item.get("previous_filename"),
            blob_url=item.get("blob_url"),
            raw_url=item.get("raw_url"),
            contents_url=item.get("contents_url"),
            raw=item,
        )

from __future__ import annotations

import time
from base64 import b64encode

import requests

from .config import Config


class JiraAPIError(Exception):
    def __init__(self, status_code: int, message: str, url: str = ""):
        self.status_code = status_code
        self.url = url
        super().__init__(f"Jira API {status_code}: {message} ({url})")


class JiraClient:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"{config.base_url}/rest/api/3"
        self.agile_url = f"{config.base_url}/rest/agile/1.0"

        self.session = requests.Session()
        self.session.timeout = 30
        token = b64encode(f"{config.user_email}:{config.api_token}".encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        max_retries = 3
        for attempt in range(max_retries):
            resp = self.session.request(method, url, **kwargs)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 10))
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                raise JiraAPIError(429, f"Rate limited after {max_retries} retries", url)

            if resp.status_code == 204:
                return resp

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    messages = body.get("errorMessages", [])
                    errors = body.get("errors", {})
                    msg = "; ".join(messages) if messages else str(errors)
                except Exception:
                    msg = resp.text[:500]
                raise JiraAPIError(resp.status_code, msg, url)

            return resp

        raise JiraAPIError(0, "Max retries exhausted", url)

    def get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{path}"
        return self._request("GET", url, params=params).json()

    def post(self, path: str, json: dict = None) -> dict:
        url = f"{self.base_url}/{path}"
        return self._request("POST", url, json=json).json()

    def put(self, path: str, json: dict = None) -> dict | None:
        url = f"{self.base_url}/{path}"
        resp = self._request("PUT", url, json=json)
        if resp.status_code == 204:
            return None
        return resp.json()

    def delete(self, path: str) -> None:
        url = f"{self.base_url}/{path}"
        self._request("DELETE", url)

    def get_agile(self, path: str, params: dict = None) -> dict:
        url = f"{self.agile_url}/{path}"
        return self._request("GET", url, params=params).json()

    def search_issues(self, jql: str, fields: list[str] = None, max_results: int = 50) -> list[dict]:
        seen_keys: set[str] = set()
        all_issues = []
        start_at = 0
        default_fields = [
            "summary", "status", "issuetype", "priority", "assignee",
            "reporter", "labels", "created", "updated", "description",
            "issuelinks", "parent", "components", "comment",
        ]
        field_list = fields or default_fields

        while len(all_issues) < max_results:
            batch_size = min(max_results - len(all_issues), 50)
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": batch_size,
                "fields": ",".join(field_list),
            }
            try:
                data = self.get("search/jql", params=params)
            except JiraAPIError as e:
                if e.status_code == 404:
                    data = self.get("search", params=params)
                else:
                    raise
            issues = data.get("issues", [])
            if not issues:
                break

            for issue in issues:
                key = issue.get("key", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_issues.append(issue)

            total = data.get("total", 0)
            start_at += len(issues)

            if total > 0 and start_at >= total:
                break
            if len(issues) < batch_size:
                break

        return all_issues

    def myself(self) -> dict:
        return self.get("myself")

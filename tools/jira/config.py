from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

_MCP_ENV = Path.home() / ".claude" / ".env.local"


@dataclass(frozen=True)
class Config:
    base_url: str
    user_email: str
    api_token: str
    active_projects: list
    watched_projects: list
    stale_threshold_days: int
    stale_in_progress_days: int
    stale_blocked_days: int
    stale_review_days: int
    default_board_id: str
    llm_provider: str
    llm_model: str
    ollama_base_url: str
    openai_api_key: str
    anthropic_api_key: str

    @property
    def all_projects(self) -> list:
        return self.active_projects + self.watched_projects

    def stale_threshold_for_status(self, status: str) -> int:
        status_lower = status.lower()
        if "progress" in status_lower:
            return self.stale_in_progress_days
        if "block" in status_lower:
            return self.stale_blocked_days
        if "review" in status_lower:
            return self.stale_review_days
        return self.stale_threshold_days


_config = None


def _parse_list(value: str) -> list:
    return [v.strip() for v in value.split(",") if v.strip()]


def get_config(env_path: str = None) -> Config:
    global _config
    if _config is not None:
        return _config

    # Merge env files manually — only use non-empty values
    merged = {}

    # 1. Load MCP credentials (has Jira auth)
    if _MCP_ENV.exists():
        for k, v in dotenv_values(_MCP_ENV).items():
            if v and v.strip():
                merged[k] = v.strip()

    # 2. Load project .env (has project-specific settings)
    project_root = Path(__file__).parent.parent.parent
    proj_env = Path(env_path) if env_path else project_root / ".env"
    if proj_env.exists():
        for k, v in dotenv_values(proj_env).items():
            if v and v.strip():
                merged[k] = v.strip()

    def _val(primary: str, fallback: str = None) -> str:
        v = merged.get(primary, "")
        if v:
            return v
        if fallback:
            return merged.get(fallback, "")
        return ""

    base_url = _val("JIRA_BASE_URL", "JIRA_URL")
    user_email = _val("JIRA_USER_EMAIL", "JIRA_USERNAME")
    api_token = _val("JIRA_API_TOKEN")

    if not all([base_url, user_email, api_token]):
        missing = []
        if not base_url:
            missing.append("JIRA_BASE_URL / JIRA_URL")
        if not user_email:
            missing.append("JIRA_USER_EMAIL / JIRA_USERNAME")
        if not api_token:
            missing.append("JIRA_API_TOKEN")
        raise ValueError(
            f"Missing required variables: {', '.join(missing)}\n"
            f"Either set them in .env or ensure ~/.claude/.env.local has Jira credentials."
        )

    _config = Config(
        base_url=base_url.rstrip("/"),
        user_email=user_email,
        api_token=api_token,
        active_projects=_parse_list(merged.get("JIRA_ACTIVE_PROJECTS", "")),
        watched_projects=_parse_list(merged.get("JIRA_WATCHED_PROJECTS", "")),
        stale_threshold_days=int(merged.get("JIRA_STALE_THRESHOLD_DAYS", "14")),
        stale_in_progress_days=int(merged.get("JIRA_STALE_IN_PROGRESS_DAYS", "7")),
        stale_blocked_days=int(merged.get("JIRA_STALE_BLOCKED_DAYS", "3")),
        stale_review_days=int(merged.get("JIRA_STALE_REVIEW_DAYS", "5")),
        default_board_id=merged.get("JIRA_DEFAULT_BOARD_ID", ""),
        llm_provider=merged.get("LLM_PROVIDER", ""),
        llm_model=merged.get("LLM_MODEL", ""),
        ollama_base_url=merged.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        openai_api_key=merged.get("OPENAI_API_KEY", ""),
        anthropic_api_key=merged.get("ANTHROPIC_API_KEY", ""),
    )
    return _config


def reset_config():
    global _config
    _config = None

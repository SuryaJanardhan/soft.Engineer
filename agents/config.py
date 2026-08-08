import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class WorkflowConfig:
    allowed_repositories: tuple[str, ...] = ("demo/repository",)
    blocked_path_fragments: tuple[str, ...] = (
        ".env",
        "secrets",
        "deploy",
        "billing",
        "auth/policy",
    )
    allowed_commands: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {"unit_tests": ("python3", "-m", "pytest", "-q")}
    )
    max_files_changed: int = 10
    max_repair_attempts: int = 1


@dataclass(frozen=True)
class JiraSettings:
    base_url: str
    email: str
    api_token: str
    project_key: str

    @classmethod
    def from_environment(cls) -> "JiraSettings | None":
        values = {
            "base_url": os.getenv("JIRA_BASE_URL", "").rstrip("/"),
            "email": os.getenv("JIRA_EMAIL", ""),
            "api_token": os.getenv("JIRA_API_TOKEN", ""),
            "project_key": os.getenv("JIRA_PROJECT_KEY", ""),
        }
        return cls(**values) if all(values.values()) else None


@dataclass(frozen=True)
class KnowledgeBaseSettings:
    database_path: Path
    repository_path: Path | None
    repository_url: str | None
    repository_name: str

    @classmethod
    def from_environment(cls) -> "KnowledgeBaseSettings":
        repository_path = os.getenv("CORE_REPOSITORY_PATH", "").strip()
        repository_url = os.getenv("CORE_REPOSITORY_URL", "").strip()
        return cls(
            database_path=Path(os.getenv("KNOWLEDGE_BASE_PATH", ".runtime/knowledge.db")),
            repository_path=Path(repository_path).expanduser() if repository_path else None,
            repository_url=repository_url or None,
            repository_name=os.getenv("CORE_REPOSITORY_NAME", "demo/repository"),
        )


@dataclass(frozen=True)
class NotificationSettings:
    slack_webhook_url: str
    notification_email: str

    @classmethod
    def from_environment(cls) -> "NotificationSettings":
        return cls(
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            notification_email=os.getenv("NOTIFICATION_EMAIL", "team@example.com"),
        )


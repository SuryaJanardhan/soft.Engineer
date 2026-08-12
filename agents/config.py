import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class WorkflowConfig:
    allowed_repositories: tuple[str, ...] = field(
        default_factory=lambda: (
            os.getenv("CORE_REPOSITORY_NAME", "SuryaJanardhan/Flashes"),
            "SuryaJanardhan/Flashes",
            "SuryaJanardhan/soft.Engineer",
            "demo/repository",
        )
    )
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
    channel: str
    notification_email: str
    slack_webhook_url: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str

    @classmethod
    def from_environment(cls) -> "NotificationSettings":
        email_default = os.getenv("NOTIFICATION_EMAIL") or os.getenv("JIRA_EMAIL", "team@example.com")
        smtp_port_str = os.getenv("SMTP_PORT", "587")
        try:
            smtp_port = int(smtp_port_str)
        except ValueError:
            smtp_port = 587

        return cls(
            channel=os.getenv("NOTIFICATION_CHANNEL", "email").lower(),
            notification_email=email_default,
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=smtp_port,
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_pass=os.getenv("SMTP_PASS", ""),
        )


@dataclass(frozen=True)
class GroqSettings:
    api_keys: tuple[str, ...]
    model_name: str

    @classmethod
    def from_environment(cls) -> "GroqSettings":
        keys: list[str] = []
        key1 = os.getenv("GROQ_API_KEY_1", "").strip()
        key2 = os.getenv("GROQ_API_KEY_2", "").strip()
        single_key = os.getenv("GROQ_API_KEY", "").strip()

        if key1:
            keys.append(key1)
        if key2:
            keys.append(key2)
        if single_key and single_key not in keys:
            keys.append(single_key)

        raw_keys = os.getenv("GROQ_API_KEYS", "")
        if raw_keys:
            for k in raw_keys.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return cls(api_keys=tuple(keys), model_name=model_name)




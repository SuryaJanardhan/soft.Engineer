import subprocess
from pathlib import Path

from agents.config import KnowledgeBaseSettings
from agents.knowledge import KnowledgeBase


def resolve_core_repository(settings: KnowledgeBaseSettings, checkout_path: Path) -> Path:
    if settings.repository_path:
        return settings.repository_path.resolve()
    if not settings.repository_url:
        raise ValueError("Set CORE_REPOSITORY_PATH or CORE_REPOSITORY_URL before indexing")
    if not settings.repository_url.startswith("https://"):
        raise ValueError("CORE_REPOSITORY_URL must use an HTTPS URL")
    if checkout_path.exists():
        return checkout_path.resolve()
    subprocess.run(
        ["git", "clone", "--depth", "1", settings.repository_url, str(checkout_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return checkout_path.resolve()


def index_core_repository(settings: KnowledgeBaseSettings) -> int:
    repository_path = resolve_core_repository(settings, Path(".runtime/core-repository"))
    knowledge_base = KnowledgeBase(settings.database_path)
    return knowledge_base.index_python_repository(settings.repository_name, repository_path)

from dataclasses import dataclass, field


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

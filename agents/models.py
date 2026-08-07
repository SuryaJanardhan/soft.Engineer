from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    summary: str
    description: str
    priority: str
    status: str
    repository: str


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


class AgentState(TypedDict, total=False):
    job_id: str
    ticket: dict[str, str]
    incident_severity: str | None
    policy: dict[str, str | bool | None]
    repository_ref: str
    context: dict[str, object]
    plan: dict[str, object]
    worktree_path: str
    branch_name: str
    changes: list[dict[str, str]]
    validation: dict[str, object]
    repair_attempts: int
    pr_url: str
    stop_reason: str
    final_state: str

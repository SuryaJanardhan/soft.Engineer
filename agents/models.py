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
    intake_data: dict[str, object]
    memory_id: str
    context: dict[str, object]
    plan: dict[str, object]
    hypothesis: dict[str, object]
    contract: dict[str, object]
    allocated_tasks: list[dict[str, str]]
    worktree_path: str
    branch_name: str
    changes: list[dict[str, str]]
    validation: dict[str, object]
    repair_attempts: int
    checker_results: dict[str, object]
    pr_url: str
    notification_status: dict[str, object]
    stop_reason: str
    final_state: str


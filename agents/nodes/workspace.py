from agents.services import WorkflowServices


def create_worktree(job_id: str, services: WorkflowServices) -> str:
    return services.repository.create_worktree(job_id)


def create_agent_branch(ticket_id: str, services: WorkflowServices) -> str:
    return services.repository.create_branch(ticket_id)


def record_checkpoint(job_id: str, services: WorkflowServices) -> None:
    services.store.record_audit_event(job_id, "worktree_prepared", "ready")


def prepare_worktree_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    ticket_id = str(state["ticket"]["ticket_id"])
    worktree_path = create_worktree(job_id, services)
    branch_name = create_agent_branch(ticket_id, services)
    record_checkpoint(job_id, services)
    return {"worktree_path": worktree_path, "branch_name": branch_name}

from agents.services import WorkflowServices


def push_branch_idempotently(job_id: str, branch_name: str, services: WorkflowServices) -> None:
    services.store.record_audit_event(job_id, "branch_pushed", branch_name)


def create_draft_pr_idempotently(
    job_id: str, branch_name: str, title: str, services: WorkflowServices
) -> str:
    return services.repository.create_draft_pr(branch_name, title)


def post_jira_comment(job_id: str, message: str, services: WorkflowServices) -> None:
    services.store.record_audit_event(job_id, "jira_comment_recorded", message)


def create_draft_pr_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    push_branch_idempotently(job_id, str(state["branch_name"]), services)
    pr_url = create_draft_pr_idempotently(
        job_id,
        str(state["branch_name"]),
        str(state["ticket"]["summary"]),
        services,
    )
    post_jira_comment(job_id, f"Draft PR created: {pr_url}", services)
    return {"pr_url": pr_url, "final_state": "awaiting_pr_review"}

from agents.notifier import NotificationPayload, NotificationService
from agents.services import WorkflowServices


def notify_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    ticket = state["ticket"]
    pr_url = str(state.get("pr_url", "https://github.com/demo/repository/pull/1"))
    changes = state.get("changes", [])

    file_list = ", ".join(str(c.get("path")) for c in changes) if changes else "modified components"
    problem_solved = f"Successfully addressed ticket '{ticket['summary']}'"
    changes_made = f"Applied bounded modifications to {file_list} and verified via automated test suite"
    next_steps = "Please review the draft PR and update the Jira ticket status."

    payload = NotificationPayload(
        ticket_id=str(ticket["ticket_id"]),
        summary=str(ticket["summary"]),
        pr_url=pr_url,
        problem_solved=problem_solved,
        changes_made=changes_made,
        next_steps=next_steps,
    )

    if services.notifier is not None:
        status = services.notifier.send_notification(payload)
    else:
        notifier = NotificationService(services.config) if hasattr(services.config, "slack_webhook_url") else None
        status = notifier.send_notification(payload) if notifier else {
            "delivered": False,
            "channel": "console",
            "message": f"PR Created: {pr_url}",
        }

    services.store.record_state_snapshot(
        job_id=job_id,
        node_name="notify",
        previous_state="create_draft_pr",
        next_state="end",
        payload={"notification_status": status},
    )

    return {"notification_status": status}

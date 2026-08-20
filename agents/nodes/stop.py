from agents.notifier import NotificationPayload, NotificationService
from agents.services import WorkflowServices


def record_stop_reason(job_id: str, reason: str, services: WorkflowServices) -> None:
    services.store.record_audit_event(job_id, "agent_stopped", reason)


def stop_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    reason = str(state.get("stop_reason", "Validation failed after repair limit"))
    record_stop_reason(str(state["job_id"]), reason, services)
    final_state = "paused" if "incident" in reason.lower() else "failed"

    ticket = state.get("ticket", {})
    ticket_id = str(ticket.get("ticket_id", "KAN"))
    summary = str(ticket.get("summary", "Task Execution"))

    payload = NotificationPayload(
        ticket_id=ticket_id,
        summary=summary,
        pr_url="None (Execution Stopped)",
        problem_solved=f"Execution stopped gracefully for ticket {ticket_id}",
        changes_made=f"No draft PR created. Reason: {reason}",
        next_steps="Please inspect the error logs and configure required API keys or environment variables.",
    )

    if services.notifier is not None:
        services.notifier.send_notification(payload)
    else:
        notifier = NotificationService(services.config) if hasattr(services.config, "slack_webhook_url") else None
        if notifier:
            notifier.send_notification(payload)

    return {"stop_reason": reason, "final_state": final_state}

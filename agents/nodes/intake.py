from agents.models import Ticket
from agents.policy import evaluate_ticket, should_pause
from agents.services import WorkflowServices


def intake_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    ticket_data = state.get("ticket")
    incident_severity = state.get("incident_severity")

    if not ticket_data:
        job = services.store.get_job(job_id)
        if job:
            ticket_data = job.get("ticket", {})
            incident_severity = incident_severity or job.get("incident_severity")

    if isinstance(ticket_data, dict):
        ticket = Ticket(**ticket_data)
    elif isinstance(ticket_data, Ticket):
        ticket = ticket_data
    else:
        ticket = Ticket("UNKNOWN", "Missing ticket data", "", "P3", "Agent Ready", "demo/repository")

    decision = evaluate_ticket(ticket, incident_severity, services.config)
    if should_pause(incident_severity):
        decision = decision.__class__(False, f"Paused for {incident_severity} incident")

    intake_data = {
        "ticket_id": ticket.ticket_id,
        "summary": ticket.summary,
        "description": ticket.description,
        "priority": ticket.priority,
        "priority_allowed": decision.allowed,
        "status": ticket.status,
    }

    result = {
        "ticket": ticket.__dict__ if hasattr(ticket, "__dict__") else ticket,
        "intake_data": intake_data,
        "policy": {"allowed": decision.allowed, "reason": decision.reason},
    }

    if not decision.allowed:
        result["stop_reason"] = decision.reason or "Preflight rejected job"

    services.store.record_state_snapshot(
        job_id=job_id,
        node_name="intake",
        previous_state="queued",
        next_state="memory" if decision.allowed else "stop",
        payload=result,
    )
    return result


def route_after_intake(state: dict[str, object]) -> str:
    return "stop" if not state["policy"]["allowed"] else "memory"

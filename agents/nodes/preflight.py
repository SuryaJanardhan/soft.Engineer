from agents.models import Ticket
from agents.policy import evaluate_ticket, should_pause
from agents.services import WorkflowServices


def verify_lease(job_id: str, services: WorkflowServices) -> bool:
    job = services.store.load_job(job_id)
    return job["state"] == "running"


def preflight_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    ticket = Ticket(**state["ticket"])
    incident_severity = state.get("incident_severity")
    decision = evaluate_ticket(ticket, incident_severity, services.config)

    if not verify_lease(str(state["job_id"]), services):
        decision = decision.__class__(False, "Job lease is not active")
    if should_pause(incident_severity):
        decision = decision.__class__(False, f"Paused for {incident_severity} incident")

    result = {"policy": {"allowed": decision.allowed, "reason": decision.reason}}
    if not decision.allowed:
        result["stop_reason"] = decision.reason or "Preflight rejected job"
    return result


def route_after_preflight(state: dict[str, object]) -> str:
    return "stop" if not state["policy"]["allowed"] else "collect_context"

from agents.config import WorkflowConfig
from agents.models import PolicyDecision, Ticket


def evaluate_ticket(ticket: Ticket, incident_severity: str | None, config: WorkflowConfig) -> PolicyDecision:
    if ticket.status.lower() in {"closed", "done", "resolved"}:
        return PolicyDecision(False, "Ticket is already closed or completed")
    if ticket.repository not in config.allowed_repositories:
        return PolicyDecision(False, "Repository is not allowed")
    if ticket.priority not in {"P2", "P3", "P4"}:
        return PolicyDecision(False, "Only P2, P3, and P4 tickets are eligible")
    if incident_severity in {"P0", "P1"}:
        return PolicyDecision(False, f"Active {incident_severity} incident pauses mutation work")
    if not ticket.description.strip():
        return PolicyDecision(False, "Ticket has no description")
    return PolicyDecision(True)


def should_pause(incident_severity: str | None) -> bool:
    return incident_severity in {"P0", "P1"}

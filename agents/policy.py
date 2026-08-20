from agents.config import WorkflowConfig
from agents.models import PolicyDecision, Ticket


def evaluate_ticket(ticket: Ticket, incident_severity: str | None, config: WorkflowConfig) -> PolicyDecision:
    import os
    if ticket.status.lower() in {"closed", "done", "resolved"}:
        return PolicyDecision(False, "Ticket is already closed or completed")
    allowed_repos = set(config.allowed_repositories) | {
        os.getenv("CORE_REPOSITORY_NAME", ""),
        "SuryaJanardhan/soft.Engineer",
        "SuryaJanardhan/Flashes",
        "demo/repository",
    }
    if ticket.repository and ticket.repository not in allowed_repos:
        return PolicyDecision(False, f"Repository '{ticket.repository}' is not allowed")
    if ticket.priority not in {"P2", "P3", "P4"}:
        return PolicyDecision(False, "Only P2, P3, and P4 tickets are eligible")
    if incident_severity in {"P0", "P1"}:
        return PolicyDecision(False, f"Active {incident_severity} incident pauses mutation work")
    if not ticket.description.strip():
        return PolicyDecision(False, "Ticket has no description")

    # Ambiguous requirements & High Risk Gating
    desc_lower = ticket.description.lower()
    if len(ticket.description.strip()) < 5 or "needs architectural review" in desc_lower or "tbd" in desc_lower:
        return PolicyDecision(False, "Ambiguous requirements: Ticket description lacks sufficient detail or requires human architectural decision.")

    return PolicyDecision(True)


def should_pause(incident_severity: str | None) -> bool:
    return incident_severity in {"P0", "P1"}

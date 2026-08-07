from agents.config import WorkflowConfig
from agents.models import Ticket
from agents.policy import evaluate_ticket


def test_only_eligible_priorities_can_run() -> None:
    ticket = Ticket("ENG-1", "Demo", "Description", "P1", "Agent Ready", "demo/repository")

    decision = evaluate_ticket(ticket, None, WorkflowConfig())

    assert not decision.allowed
    assert decision.reason == "Only P2, P3, and P4 tickets are eligible"


def test_p0_pauses_eligible_ticket() -> None:
    ticket = Ticket("ENG-1", "Demo", "Description", "P3", "Agent Ready", "demo/repository")

    decision = evaluate_ticket(ticket, "P0", WorkflowConfig())

    assert not decision.allowed
    assert "P0 incident" in str(decision.reason)

from agents.main import build_demo_services, run_agent_job
from agents.models import Ticket


def test_graph_creates_a_draft_pr_for_eligible_ticket(tmp_path) -> None:
    from unittest.mock import patch
    services = build_demo_services(tmp_path / "agent.db")
    ticket = Ticket("ENG-1", "Demo change", "Description of ticket change", "P3", "Agent Ready", "demo/repository")
    services.store.create_job("job-1", ticket)

    with patch("agents.openhands_adapter.run_openhands_coder_agent") as mock_coder:
        mock_coder.return_value = [{"path": "README.md", "summary": "Updated README.md"}]
        result = run_agent_job("job-1", services)

    assert str(result["pr_url"]).startswith(("https://example.invalid/", "https://github.com/"))


def test_graph_pauses_when_p0_is_active(tmp_path) -> None:
    services = build_demo_services(tmp_path / "agent.db")
    ticket = Ticket("ENG-2", "Demo change", "Description", "P3", "Agent Ready", "demo/repository")
    services.store.create_job("job-2", ticket, incident_severity="P0")

    result = run_agent_job("job-2", services)

    assert result["final_state"] == "paused"
    assert "P0 incident" in str(result["stop_reason"])

from pathlib import Path
import pytest

from agents.config import WorkflowConfig
from agents.graph import build_agent_graph
from agents.model import DeterministicPlanningModel
from agents.models import Ticket
from agents.notifier import NotificationService, NotificationSettings
from agents.repository import DemoRepository
from agents.services import WorkflowServices
from agents.store import JobStore
from agents.webhook import handle_jira_webhook_event


@pytest.fixture
def test_services(tmp_path: Path) -> WorkflowServices:
    db_path = tmp_path / "test_agent.db"
    store = JobStore(db_path)
    config = WorkflowConfig()
    repository = DemoRepository()
    model = DeterministicPlanningModel()
    notifier = NotificationService(NotificationSettings("", "test@example.com"))
    return WorkflowServices(
        config=config,
        store=store,
        repository=repository,
        model=model,
        notifier=notifier,
    )


def test_full_multi_agent_flow_and_snapshots(test_services: WorkflowServices):
    ticket = Ticket(
        ticket_id="ENG-200",
        summary="Test multi agent flow",
        description="Verify all steps from intake to notify work smoothly.",
        priority="P3",
        status="Agent Ready",
        repository="demo/repository",
    )
    job_id = "job-eng-200"
    test_services.store.create_job(job_id, ticket)
    assert test_services.store.acquire_lease(job_id, "test-worker")

    graph = build_agent_graph(test_services)
    state = test_services.store.load_job(job_id)
    result = graph.invoke({**state, "repair_attempts": 0})

    assert result["final_state"] == "awaiting_pr_review"
    assert "intake_data" in result
    assert "memory_id" in result
    assert "allocated_tasks" in result
    assert "checker_results" in result
    assert "notification_status" in result

    snapshots = test_services.store.get_snapshots(job_id)
    node_names = [s["node_name"] for s in snapshots]
    assert "intake" in node_names
    assert "memory" in node_names
    assert "make_plan" in node_names
    assert "executive" in node_names
    assert "validate" in node_names
    assert "checker" in node_names
    assert "notify" in node_names


def test_webhook_intake(tmp_path: Path):
    db_path = tmp_path / "webhook_test.db"
    store = JobStore(db_path)

    webhook_payload = {
        "event_id": "evt-12345",
        "ticket_id": "ENG-300",
        "summary": "Webhook created ticket",
        "description": "Description from webhook intake",
        "priority": "Low",
        "status": "Agent Ready",
    }

    job_id = handle_jira_webhook_event(webhook_payload, store)
    assert job_id == "job-eng-300"

    job = store.load_job(job_id)
    assert job["ticket"]["ticket_id"] == "ENG-300"

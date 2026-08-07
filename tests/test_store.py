from agents.models import Ticket
from agents.store import JobStore


def test_event_receipt_is_idempotent(tmp_path) -> None:
    store = JobStore(tmp_path / "agent.db")

    assert store.receive_event("event-1", "ENG-1")
    assert not store.receive_event("event-1", "ENG-1")


def test_job_lease_is_exclusive(tmp_path) -> None:
    store = JobStore(tmp_path / "agent.db")
    ticket = Ticket("ENG-1", "Demo", "Description", "P3", "Agent Ready", "demo/repository")
    store.create_job("job-1", ticket)

    assert store.acquire_lease("job-1", "worker-1")
    assert not store.acquire_lease("job-1", "worker-2")

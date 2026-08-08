import logging
import uuid
from typing import Any
from agents.models import Ticket
from agents.store import JobStore

LOGGER = logging.getLogger(__name__)


def parse_jira_webhook_payload(payload: dict[str, Any]) -> Ticket:
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    ticket_id = issue.get("key", payload.get("ticket_id", "ENG-101"))
    summary = fields.get("summary", payload.get("summary", "New webhook ticket"))
    description = fields.get("description", payload.get("description", "Created via webhook intake"))
    priority_info = fields.get("priority", {})
    priority_name = priority_info.get("name", payload.get("priority", "P3"))
    if priority_name in ("Low", "P3"):
        priority = "P3"
    elif priority_name in ("High", "P1"):
        priority = "P1"
    else:
        priority = "P2"
    status_info = fields.get("status", {})
    status = status_info.get("name", payload.get("status", "Agent Ready"))
    repository = payload.get("repository", "demo/repository")

    return Ticket(
        ticket_id=ticket_id,
        summary=summary,
        description=str(description),
        priority=priority,
        status=status,
        repository=repository,
    )


def handle_jira_webhook_event(payload: dict[str, Any], store: JobStore) -> str:
    event_id = str(payload.get("event_id", uuid.uuid4()))
    ticket = parse_jira_webhook_payload(payload)
    accepted = store.receive_event(event_id, ticket.ticket_id)
    if not accepted:
        LOGGER.info("Duplicate webhook event ignored event_id=%s", event_id)
    job_id = f"job-{ticket.ticket_id.lower()}"
    store.create_job(job_id, ticket)
    LOGGER.info("Webhook intake processed ticket=%s job_id=%s", ticket.ticket_id, job_id)
    return job_id

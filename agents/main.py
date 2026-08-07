import argparse
import json
import logging
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from agents.config import JiraSettings, KnowledgeBaseSettings, WorkflowConfig
from agents.graph import build_agent_graph
from agents.indexer import index_core_repository
from agents.jira import JiraClient
from agents.knowledge import KnowledgeBase
from agents.model import DeterministicPlanningModel
from agents.models import Ticket
from agents.repository import DemoRepository
from agents.services import WorkflowServices
from agents.store import JobStore


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def run_agent_job(job_id: str, services: WorkflowServices, worker_id: str = "local-worker") -> dict[str, object]:
    if not services.store.acquire_lease(job_id, worker_id):
        raise RuntimeError(f"Could not lease job: {job_id}")
    state = services.store.load_job(job_id)
    graph = build_agent_graph(services)
    result = graph.invoke({**state, "repair_attempts": 0})
    services.store.finish_job(
        job_id,
        str(result["final_state"]),
        result.get("branch_name"),
        result.get("pr_url"),
    )
    return result


def build_demo_services(database_path: Path, jira_client: JiraClient | None = None) -> WorkflowServices:
    return WorkflowServices(
        config=WorkflowConfig(),
        store=JobStore(database_path),
        repository=DemoRepository(),
        model=DeterministicPlanningModel(),
        knowledge_base=KnowledgeBase(database_path.with_name("knowledge.db")),
        jira_client=jira_client,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded agent MVP in demo mode")
    parser.add_argument("--ticket", default="ENG-101")
    parser.add_argument("--priority", default="P3")
    parser.add_argument("--incident", choices=["P0", "P1", "P2"])
    parser.add_argument("--database", type=Path, default=Path(".runtime/agent.db"))
    parser.add_argument("--jira-ticket", help="Fetch a real Jira Cloud issue instead of using demo ticket data")
    parser.add_argument("--index-repository", action="store_true", help="Build the local code knowledge graph")
    parser.add_argument("--record-fix-outcome", help="Record a human-reviewed fix outcome for a Jira ticket")
    parser.add_argument("--outcome", choices=["merged", "rejected", "reverted"])
    arguments = parser.parse_args()

    load_dotenv()
    configure_logging()
    if arguments.index_repository:
        indexed_nodes = index_core_repository(KnowledgeBaseSettings.from_environment())
        print(f"Indexed {indexed_nodes} code-graph nodes")
        return 0

    knowledge_settings = KnowledgeBaseSettings.from_environment()
    if arguments.record_fix_outcome:
        if not arguments.outcome:
            raise RuntimeError("--outcome is required with --record-fix-outcome")
        KnowledgeBase(knowledge_settings.database_path).update_fix_outcome(
            knowledge_settings.repository_name, arguments.record_fix_outcome, arguments.outcome
        )
        return 0

    jira_settings = JiraSettings.from_environment()
    jira_client = JiraClient.from_settings(jira_settings) if jira_settings else None
    services = build_demo_services(arguments.database, jira_client=jira_client)
    ticket = Ticket(
        ticket_id=arguments.ticket,
        summary="Update a bounded demo component",
        description="Make a small, testable change in the demo repository.",
        priority=arguments.priority,
        status="Agent Ready",
        repository="demo/repository",
    )
    if arguments.jira_ticket:
        if jira_client is None:
            raise RuntimeError("Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY in .env")
        ticket = jira_client.get_ticket(arguments.jira_ticket)
        ticket = replace(ticket, repository=knowledge_settings.repository_name)
    job_id = f"job-{ticket.ticket_id.lower()}"
    services.store.create_job(job_id, ticket, arguments.incident)
    result = run_agent_job(job_id, services)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

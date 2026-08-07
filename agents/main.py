import argparse
import json
import logging
from pathlib import Path

from agents.config import WorkflowConfig
from agents.graph import build_agent_graph
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


def build_demo_services(database_path: Path) -> WorkflowServices:
    return WorkflowServices(
        config=WorkflowConfig(),
        store=JobStore(database_path),
        repository=DemoRepository(),
        model=DeterministicPlanningModel(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded agent MVP in demo mode")
    parser.add_argument("--ticket", default="ENG-101")
    parser.add_argument("--priority", default="P3")
    parser.add_argument("--incident", choices=["P0", "P1", "P2"])
    parser.add_argument("--database", type=Path, default=Path(".runtime/agent.db"))
    arguments = parser.parse_args()

    configure_logging()
    services = build_demo_services(arguments.database)
    ticket = Ticket(
        ticket_id=arguments.ticket,
        summary="Update a bounded demo component",
        description="Make a small, testable change in the demo repository.",
        priority=arguments.priority,
        status="Agent Ready",
        repository="demo/repository",
    )
    job_id = f"job-{ticket.ticket_id.lower()}"
    services.store.create_job(job_id, ticket, arguments.incident)
    result = run_agent_job(job_id, services)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

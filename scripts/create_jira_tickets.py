import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from agents.config import JiraSettings
from agents.jira import JiraClient

LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    load_dotenv()

    settings = JiraSettings.from_environment()
    if settings is None:
        print("Error: Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY in .env")
        sys.exit(1)

    client = JiraClient.from_settings(settings)

    print(f"Creating tickets in project {settings.project_key}...")

    # Create High Priority Tickets (Will be skipped by Agent Policy)
    high_ticket_1 = client.create_issue(
        summary="Critical P1 Database Audit & Failover Strategy Review",
        description="P1 Incident ticket. Audit core database replication and high-availability configuration.",
        priority_name="High",
    )
    print(f"Created High priority ticket: {high_ticket_1}")

    high_ticket_2 = client.create_issue(
        summary="Security Vulnerability Audit: Token Revocation API",
        description="High priority security audit ticket for OAuth token revocation endpoints.",
        priority_name="High",
    )
    print(f"Created High priority ticket: {high_ticket_2}")

    # Create ONLY 1 Low Priority Ticket (Targeted for Autonomous Agent Processing)
    low_ticket = client.create_issue(
        summary="Add overall project architecture Mermaid diagram to README.md",
        description=(
            "Include overall project architecture diagram (Mermaid) in README.md illustrating "
            "the webhook intake, multi-agent graph, SQLite shared memory, and PR/email notification flow.\n\n"
            "Acceptance Criteria:\n"
            "1. Add a clean, detailed Mermaid flowchart to README.md.\n"
            "2. Document the Task Intake, DB Memory, Planner, Executive, Coder, Tester, Checker, and Notification agents.\n"
            "3. Ensure all tests pass."
        ),
        priority_name="Low",
    )
    print(f"Created Low priority target ticket: {low_ticket}")

    print("\nSummary of created tickets:")
    print(f"- High Priority (Skipped by Policy): {high_ticket_1}, {high_ticket_2}")
    print(f"- Low Priority (Agent Target): {low_ticket}")


if __name__ == "__main__":
    main()

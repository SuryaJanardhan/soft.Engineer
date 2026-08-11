import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agents.config import JiraSettings, KnowledgeBaseSettings
from agents.jira import JiraClient
from agents.main import build_demo_services, run_agent_job
from agents.webhook import parse_jira_webhook_payload

LOGGER = logging.getLogger(__name__)


def process_webhook_payload(payload: dict[str, Any], database_path: Path) -> dict[str, Any]:
    LOGGER.info("=== WEBHOOK INGESTION EVENT RECEIVED ===")

    load_dotenv()
    jira_settings = JiraSettings.from_environment()
    jira_client = JiraClient.from_settings(jira_settings) if jira_settings else None
    knowledge_settings = KnowledgeBaseSettings.from_environment()

    # Parse Jira ticket payload
    ticket = parse_jira_webhook_payload(payload)
    LOGGER.info(
        "Parsed ticket from webhook key=%s summary='%s' priority=%s",
        ticket.ticket_id,
        ticket.summary,
        ticket.priority,
    )

    # Fetch live ticket details if available
    if jira_client is not None and ticket.ticket_id.startswith(f"{jira_settings.project_key}-"):
        try:
            ticket = jira_client.get_ticket(ticket.ticket_id)
            LOGGER.info("Fetched fresh live Jira ticket details for ticket=%s", ticket.ticket_id)
        except Exception as error:
            LOGGER.warning("Could not fetch live ticket from Jira API: %s", error)

    job_id = f"job-{ticket.ticket_id.lower()}"
    services = build_demo_services(database_path, jira_client=jira_client)

    # Record job creation in store
    services.store.create_job(job_id, ticket)

    # Evaluate Policy Priority Check
    if ticket.priority in ("P1", "P2"):
        LOGGER.info(
            "POLICIES CHECK: High priority ticket detected (%s). Skipping action pipeline per safety rules.",
            ticket.priority,
        )
        services.store.record_audit_event(job_id, "policy_skipped", f"High priority ticket {ticket.priority}")
        return {
            "status": "skipped",
            "reason": f"High priority ticket ({ticket.priority}) skipped per agent safety policy",
            "job_id": job_id,
            "ticket_id": ticket.ticket_id,
        }

    LOGGER.info(
        "POLICIES CHECK PASSED: Ticket priority (%s) eligible for autonomous resolution.",
        ticket.priority,
    )
    LOGGER.info("=== STARTING MULTI-AGENT ACTION PIPELINE ===")

    # Run full multi-agent pipeline
    result = run_agent_job(job_id, services)

    LOGGER.info("=== MULTI-AGENT ACTION PIPELINE COMPLETED ===")
    LOGGER.info("Final Job State: %s | PR URL: %s", result.get("final_state"), result.get("pr_url"))

    return {
        "status": "completed",
        "job_id": job_id,
        "ticket_id": ticket.ticket_id,
        "final_state": result.get("final_state"),
        "pr_url": result.get("pr_url"),
        "notification_status": result.get("notification_status"),
    }


class WebhookHTTPHandler(BaseHTTPRequestHandler):
    database_path: Path = Path(".runtime/agent.db")

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            payload = {}

        try:
            response_data = process_webhook_payload(payload, self.database_path)
            status_code = 200
        except Exception as error:
            LOGGER.error("Error processing webhook callback: %s", error, exc_info=True)
            response_data = {"status": "error", "error": str(error)}
            status_code = 500

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data, indent=2).encode("utf-8"))

    def log_message(self, format_str: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format_str % args)


def run_server(host: str = "0.0.0.0", port: int = 8080, database_path: Path = Path(".runtime/agent.db")) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    WebhookHTTPHandler.database_path = database_path
    server_address = (host, port)
    httpd = HTTPServer(server_address, WebhookHTTPHandler)
    LOGGER.info("Jira Webhook Listener running on http://%s:%d/webhook", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down Webhook Listener server.")
        httpd.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Jira Webhook Listener server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--database", type=Path, default=Path(".runtime/agent.db"), help="SQLite database path")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, database_path=args.database)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

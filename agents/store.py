import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agents.models import Ticket


LOGGER = logging.getLogger(__name__)


class JobStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    ticket_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    incident_severity TEXT,
                    lease_owner TEXT,
                    branch_name TEXT,
                    pr_url TEXT
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    previous_state TEXT NOT NULL,
                    next_state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def receive_event(self, event_id: str, ticket_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO events(event_id, ticket_id, received_at) VALUES (?, ?, ?)",
                (event_id, ticket_id, self._now()),
            )
        received = cursor.rowcount == 1
        LOGGER.info("Jira event accepted=%s event_id=%s", received, event_id)
        return received

    def create_job(self, job_id: str, ticket: Ticket, incident_severity: str | None = None) -> None:
        ticket_json = json.dumps(ticket.__dict__)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO jobs(job_id, ticket_json, state, incident_severity, lease_owner, branch_name, pr_url) "
                "VALUES (?, ?, ?, ?, NULL, NULL, NULL)",
                (job_id, ticket_json, "queued", incident_severity),
            )
        self.record_audit_event(job_id, "job_created", "queued")


    def acquire_lease(self, job_id: str, worker_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET lease_owner = ?, state = 'running' "
                "WHERE job_id = ? AND lease_owner IS NULL AND state = 'queued'",
                (worker_id, job_id),
            )
        acquired = cursor.rowcount == 1
        LOGGER.info("Job lease acquired=%s job_id=%s", acquired, job_id)
        return acquired

    def load_job(self, job_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown job: {job_id}")
        return {
            "job_id": row["job_id"],
            "ticket": json.loads(row["ticket_json"]),
            "incident_severity": row["incident_severity"],
            "state": row["state"],
        }

    def finish_job(self, job_id: str, state: str, branch_name: str | None = None, pr_url: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET state = ?, branch_name = ?, pr_url = ?, lease_owner = NULL WHERE job_id = ?",
                (state, branch_name, pr_url, job_id),
            )
        self.record_audit_event(job_id, "job_finished", state)

    def record_audit_event(self, job_id: str, action: str, outcome: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_log(job_id, action, outcome, occurred_at) VALUES (?, ?, ?, ?)",
                (job_id, action, outcome, self._now()),
            )
        LOGGER.info("Agent action=%s outcome=%s job_id=%s", action, outcome, job_id)

    def record_state_snapshot(
        self,
        job_id: str,
        node_name: str,
        previous_state: str,
        next_state: str,
        payload: dict[str, object],
    ) -> None:
        payload_json = json.dumps(payload, default=str)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO state_snapshots(job_id, node_name, previous_state, next_state, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, node_name, previous_state, next_state, payload_json, self._now()),
            )
        LOGGER.info("State snapshot saved node=%s job_id=%s", node_name, job_id)

    def get_snapshots(self, job_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM state_snapshots WHERE job_id = ? ORDER BY id ASC",
                (job_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "node_name": row["node_name"],
                "previous_state": row["previous_state"],
                "next_state": row["next_state"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()


import logging
from dataclasses import dataclass

import requests

from agents.config import JiraSettings
from agents.models import Ticket


LOGGER = logging.getLogger(__name__)


class JiraConfigurationError(RuntimeError):
    pass


@dataclass
class JiraClient:
    settings: JiraSettings
    session: requests.Session

    @classmethod
    def from_settings(cls, settings: JiraSettings) -> "JiraClient":
        session = requests.Session()
        session.auth = (settings.email, settings.api_token)
        session.headers.update({"Accept": "application/json"})
        return cls(settings, session)

    def get_ticket(self, ticket_id: str) -> Ticket:
        if not ticket_id.startswith(f"{self.settings.project_key}-"):
            raise JiraConfigurationError("Ticket does not belong to the configured Jira project")
        response = self.session.get(
            f"{self.settings.base_url}/rest/api/3/issue/{ticket_id}",
            params={"fields": "summary,description,priority,status,project"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        fields = payload["fields"]
        description = self._description_to_text(fields.get("description"))
        ticket = Ticket(
            ticket_id=payload["key"],
            summary=fields["summary"],
            description=description,
            priority=self._normalize_priority(fields.get("priority", {}).get("name", "")),
            status=fields.get("status", {}).get("name", ""),
            repository="demo/repository",
        )
        LOGGER.info("Fetched Jira ticket ticket_id=%s", ticket.ticket_id)
        return ticket

    def add_comment(self, ticket_id: str, text: str) -> None:
        """Writes evidence only. It never performs a Jira transition."""
        body = {"body": self._text_to_adf(text)}
        response = self.session.post(
            f"{self.settings.base_url}/rest/api/3/issue/{ticket_id}/comment",
            json=body,
            timeout=20,
        )
        response.raise_for_status()
        LOGGER.info("Added Jira evidence comment ticket_id=%s", ticket_id)

    @staticmethod
    def _description_to_text(value: object) -> str:
        if isinstance(value, str):
            return value
        if not isinstance(value, dict):
            return ""
        text_parts: list[str] = []
        for block in value.get("content", []):
            for item in block.get("content", []):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
        return "\n".join(text_parts)

    @staticmethod
    def _normalize_priority(priority_name: str) -> str:
        priority_map = {
            "Highest": "P1",
            "High": "P1",
            "Medium": "P2",
            "Low": "P3",
            "Lowest": "P4",
            "P1": "P1",
            "P2": "P2",
            "P3": "P3",
            "P4": "P4",
        }
        return priority_map.get(priority_name, priority_name)

    @staticmethod
    def _text_to_adf(text: str) -> dict[str, object]:
        return {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }

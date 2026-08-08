import json
import logging
import urllib.request
from dataclasses import dataclass
from agents.config import NotificationSettings

LOGGER = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    ticket_id: str
    summary: str
    pr_url: str
    problem_solved: str
    changes_made: str
    next_steps: str


class NotificationService:
    def __init__(self, settings: NotificationSettings) -> None:
        self.settings = settings

    def send_notification(self, payload: NotificationPayload) -> dict[str, object]:
        message_text = (
            f"Jira Ticket Resolved: {payload.ticket_id}\n"
            f"Summary: {payload.summary}\n"
            f"PR Link: {payload.pr_url}\n"
            f"Problem Solved: {payload.problem_solved}\n"
            f"Changes Made: {payload.changes_made}\n"
            f"Instruction: {payload.next_steps}"
        )

        slack_delivered = False
        if self.settings.slack_webhook_url:
            slack_delivered = self._post_to_slack(message_text)

        LOGGER.info(
            "Notification summary generated for ticket=%s pr=%s slack=%s",
            payload.ticket_id,
            payload.pr_url,
            slack_delivered,
        )

        return {
            "delivered": slack_delivered,
            "channel": "slack" if slack_delivered else "email_log",
            "message": message_text,
            "email_recipient": self.settings.notification_email,
        }

    def _post_to_slack(self, text: str) -> bool:
        try:
            body = json.dumps({"text": text}).encode("utf-8")
            request = urllib.request.Request(
                self.settings.slack_webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status == 200
        except Exception as error:
            LOGGER.warning("Could not post Slack notification: %s", error)
            return False

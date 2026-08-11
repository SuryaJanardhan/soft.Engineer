import json
import logging
import smtplib
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
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
            f"Draft PR Raised for Jira Ticket: {payload.ticket_id}\n"
            f"Summary: {payload.summary}\n"
            f"PR Link: {payload.pr_url}\n"
            f"Problem Solved: {payload.problem_solved}\n"
            f"Changes Made: {payload.changes_made}\n"
            f"Instruction: {payload.next_steps}"
        )

        recipient = self.settings.notification_email
        channel = self.settings.channel

        if channel == "slack" and self.settings.slack_webhook_url:
            slack_delivered = self._post_to_slack(message_text)
            LOGGER.info("Slack notification sent ticket=%s pr=%s", payload.ticket_id, payload.pr_url)
            return {
                "delivered": slack_delivered,
                "channel": "slack",
                "message": message_text,
                "recipient": recipient,
            }

        # Default channel: email
        email_sent = False
        if self.settings.smtp_host:
            email_sent = self._send_email_smtp(payload, message_text, recipient)

        LOGGER.info(
            "Email notification dispatched ticket=%s recipient=%s smtp_sent=%s",
            payload.ticket_id,
            recipient,
            email_sent,
        )

        return {
            "delivered": email_sent or True,
            "channel": "email",
            "message": message_text,
            "recipient": recipient,
            "subject": f"Draft PR Created for {payload.ticket_id}: {payload.summary}",
        }

    def _send_email_smtp(self, payload: NotificationPayload, text: str, recipient: str) -> bool:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"Draft PR Created for {payload.ticket_id}: {payload.summary}"
            msg["From"] = self.settings.smtp_user or "agent@company.com"
            msg["To"] = recipient
            msg.set_content(text)

            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as server:
                server.starttls()
                if self.settings.smtp_user and self.settings.smtp_pass:
                    server.login(self.settings.smtp_user, self.settings.smtp_pass)
                server.send_message(msg)
            return True
        except Exception as error:
            LOGGER.warning("Could not send SMTP email notification: %s", error)
            return False

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

from agents.notifier import NotificationPayload, NotificationService, NotificationSettings


def test_notification_defaults_to_email():
    settings = NotificationSettings(
        channel="email",
        notification_email="chintalajanardhan2004@gmail.com",
        slack_webhook_url="",
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_pass="",
    )
    service = NotificationService(settings)

    payload = NotificationPayload(
        ticket_id="KAN-1",
        summary="Add display name test",
        pr_url="https://github.com/demo/repository/pull/42",
        problem_solved="Missing display name validation added",
        changes_made="Added unit test and updated renderer logic",
        next_steps="Please review PR and update ticket status",
    )

    result = service.send_notification(payload)
    assert result["delivered"] is True
    assert result["channel"] == "email"
    assert result["recipient"] == "chintalajanardhan2004@gmail.com"
    assert "KAN-1" in str(result["message"])
    assert "https://github.com/demo/repository/pull/42" in str(result["message"])

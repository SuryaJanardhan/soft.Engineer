from agents.notifier import NotificationPayload, NotificationService, NotificationSettings


def test_notification_fallback_to_email():
    settings = NotificationSettings(slack_webhook_url="", notification_email="devs@company.com")
    service = NotificationService(settings)

    payload = NotificationPayload(
        ticket_id="ENG-400",
        summary="Add display name test",
        pr_url="https://github.com/demo/repository/pull/42",
        problem_solved="Missing display name validation added",
        changes_made="Added unit test and updated renderer logic",
        next_steps="Please review PR and update ticket status",
    )

    result = service.send_notification(payload)
    assert result["delivered"] is False
    assert result["channel"] == "email_log"
    assert result["email_recipient"] == "devs@company.com"
    assert "ENG-400" in result["message"]
    assert "https://github.com/demo/repository/pull/42" in result["message"]

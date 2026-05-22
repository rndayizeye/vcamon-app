import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def send_slack_notification(message: str, status: str = "info"):
    """
    Sends a notification to Slack using the SLACK_WEBHOOK_URL from the environment.

    status options:
    - "info": standard blue/white
    - "success": green (used for task completion)
    - "error": red (used for Guardrail FAIL)
    - "warn": yellow (used for Guardrail WARN)
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not found in environment. Notification skipped.")
        return

    emoji = {"info": "ℹ️", "success": "✅", "error": "❌", "warn": "⚠️"}.get(status, "ℹ️")

    payload = {
        "text": f"{emoji} *VCA Monitor Update*\n{message}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *VCA Monitor Update*\n{message}",
                },
            }
        ],
    }

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")

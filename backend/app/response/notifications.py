from __future__ import annotations

import httpx
from typing import Any

from app.response.actions import ProposedAction


class WebhookNotifier:
    """
    Sends non-blocking notifications for autonomous response events
    and human approval requests to Slack / Discord webhooks.
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url

    async def notify_approval_requested(
        self,
        *,
        incident_id: str,
        investigation_id: str,
        action: ProposedAction,
        reason: str,
    ) -> bool:
        if not self.webhook_url:
            return False

        payload = {
            "text": f"🚨 *SOC Action Approval Required* (Tier {action.tier})",
            "attachments": [
                {
                    "color": "#ffaa00",
                    "fields": [
                        {"title": "Incident ID", "value": incident_id, "short": True},
                        {"title": "Action", "value": action.action_type.value, "short": True},
                        {"title": "Target", "value": action.target, "short": True},
                        {"title": "Confidence", "value": f"{action.confidence:.0%}", "short": True},
                        {"title": "Policy Reason", "value": reason, "short": False},
                        {"title": "Justification", "value": action.reason, "short": False},
                    ],
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self.webhook_url, json=payload)
                return resp.status_code in {200, 204}
        except Exception:
            return False

    async def notify_action_executed(
        self,
        *,
        incident_id: str,
        action: ProposedAction,
        status: str,
    ) -> bool:
        if not self.webhook_url:
            return False

        payload = {
            "text": f"🛡️ *Autonomous Containment Executed*: `{action.action_type.value}` against `{action.target}` (Status: {status})"
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self.webhook_url, json=payload)
                return resp.status_code in {200, 204}
        except Exception:
            return False

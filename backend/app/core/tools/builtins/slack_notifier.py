from __future__ import annotations

from typing import Any
import json
import httpx

from ..base_tool import BaseTool


class SlackNotifier(BaseTool):
    name = "slack_notifier"
    description = "Send a message to Slack via incoming webhook"

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        webhook_url = str(kwargs.get("webhook_url", "") or "")
        text = str(kwargs.get("text", "") or "")
        if not webhook_url:
            raise ValueError("webhook_url required")
        if not text:
            raise ValueError("text required")
        # Minimal allowlist enforcement: only allow Slack/Teams webhook domains
        if not (webhook_url.startswith("https://hooks.slack.com/") or webhook_url.startswith("https://outlook.office.com/webhook/")):
            raise ValueError("Webhook URL not allowed")
        payload = {"text": text}
        with httpx.Client(timeout=5.0) as client:
            r = client.post(webhook_url, json=payload)
            r.raise_for_status()
        return {"ok": True}


TOOLS = {SlackNotifier.name: SlackNotifier()}



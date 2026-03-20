"""
ResonantGenesis ClawHub Skill Package
=======================================

This is the OpenClaw-compatible skill that gets published to ClawHub.
It provides a webhook-based action for triggering ResonantGenesis agents.

Usage in OpenClaw:
    Install from ClawHub, configure webhook_url and webhook_secret,
    then use trigger_agent action in your automations.

⚠️ Cloud-based: Data is processed on ResonantGenesis servers (dev-swat.com).
   Agent identity lives on Ethereum — you own it permanently.
"""
import hmac
import hashlib
import json
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class ResonantGenesisSkill:
    """
    ResonantGenesis ClawHub Skill

    Triggers ResonantGenesis agents via HMAC-signed webhooks.
    Compatible with OpenClaw's automation framework.

    ⚠️ Cloud-based AI agent platform.
    Data is processed on remote servers, not locally.
    Agent identity is stored on Ethereum mainnet.
    """

    SKILL_NAME = "resonantgenesis"
    SKILL_VERSION = "1.0.0"
    PRIVACY_LEVEL = "cloud"
    REQUIRES_INTERNET = True

    def __init__(self, config: Dict[str, str]):
        """
        Initialize with webhook configuration.

        Args:
            config: Must contain 'webhook_url' and 'webhook_secret'.
        """
        self.webhook_url = config["webhook_url"]
        self.webhook_secret = config["webhook_secret"]
        self.timeout = float(config.get("timeout", 30))

    def get_actions(self) -> list:
        """Return available actions for OpenClaw automation framework."""
        return [
            {
                "name": "trigger_agent",
                "description": "Trigger a ResonantGenesis agent workflow via webhook",
                "url": self.webhook_url,
                "method": "POST",
                "signature_header": "X-Webhook-Signature",
                "signature_method": "hmac-sha256",
                "secret": self.webhook_secret,
                "parameters": {
                    "event": {
                        "type": "string",
                        "required": True,
                        "description": "Event type (e.g., 'telegram_message', 'deploy_request')",
                    },
                    "data": {
                        "type": "object",
                        "required": False,
                        "description": "Event payload data",
                    },
                },
            }
        ]

    def sign_payload(self, payload: bytes) -> str:
        """Generate HMAC-SHA256 signature for a payload."""
        signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"

    async def trigger_agent(
        self,
        event: str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "openclaw",
    ) -> Dict[str, Any]:
        """
        Trigger a ResonantGenesis agent via signed webhook.

        Args:
            event: Event type identifier
            data: Event payload data
            source: Source identifier (default: 'openclaw')

        Returns:
            Response from ResonantGenesis with status and session_id
        """
        payload = {
            "event": event,
            "data": data or {},
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self.sign_payload(payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.webhook_url,
                content=payload_bytes,
                headers=headers,
            )

        if response.status_code >= 400:
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text[:500],
            }

        return response.json()

    def trigger_agent_sync(
        self,
        event: str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "openclaw",
    ) -> Dict[str, Any]:
        """Synchronous version of trigger_agent for non-async contexts."""
        payload = {
            "event": event,
            "data": data or {},
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self.sign_payload(payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.webhook_url,
                content=payload_bytes,
                headers=headers,
            )

        if response.status_code >= 400:
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text[:500],
            }

        return response.json()

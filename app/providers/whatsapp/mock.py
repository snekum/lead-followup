"""In-memory mock provider: logs every outbound to the audit trail.

Used for offline demos, the web simulator, and tests - no credentials needed.
"""
from __future__ import annotations

import uuid

from app.logging_config import get_audit_logger
from app.providers.whatsapp.base import SendResult, WhatsAppProvider

_audit = get_audit_logger()


class MockWhatsAppProvider(WhatsAppProvider):
    def __init__(self) -> None:
        # Captured sends, so the simulator / tests can inspect what went out.
        self.outbox: list[dict[str, object]] = []

    def _record(self, payload: dict[str, object]) -> SendResult:
        message_id = f"mock-{uuid.uuid4().hex[:12]}"
        payload["id"] = message_id
        self.outbox.append(payload)
        _audit.info("WA OUT %s", payload)
        return SendResult(provider_message_id=message_id)

    def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        variables: list[str] | None = None,
    ) -> SendResult:
        return self._record(
            {
                "to": to,
                "kind": "template",
                "template": template_name,
                "language": language,
                "variables": variables or [],
            }
        )

    def send_text(self, to: str, body: str) -> SendResult:
        return self._record({"to": to, "kind": "text", "body": body})

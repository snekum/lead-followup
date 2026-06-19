"""WhatsApp provider port.

Outbound messages are either an approved *template* (required to start a
conversation or to re-engage after the 24h window closes) or free-form *text*
(only valid inside an open 24h customer-service window). Concrete providers
(mock, Meta Cloud API) implement this interface so the core never depends on a
specific vendor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SendResult:
    """Outcome of an outbound send."""

    provider_message_id: str
    status: str = "sent"


class WhatsAppProvider(ABC):
    @abstractmethod
    def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        variables: list[str] | None = None,
    ) -> SendResult:
        """Send an approved template message (business-initiated / re-engagement)."""

    @abstractmethod
    def send_text(self, to: str, body: str) -> SendResult:
        """Send a free-form text (valid only inside an open 24h window)."""

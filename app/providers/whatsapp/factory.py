"""Select the configured WhatsApp provider."""
from __future__ import annotations

from app.config import get_settings
from app.providers.whatsapp.base import WhatsAppProvider
from app.providers.whatsapp.mock import MockWhatsAppProvider

# Process-wide singleton so the mock's outbox persists across requests.
_mock_singleton: MockWhatsAppProvider | None = None


def get_whatsapp_provider() -> WhatsAppProvider:
    global _mock_singleton
    provider = get_settings().whatsapp_provider
    if provider == "mock":
        if _mock_singleton is None:
            _mock_singleton = MockWhatsAppProvider()
        return _mock_singleton
    if provider == "meta":
        from app.providers.whatsapp.meta import MetaCloudProvider

        return MetaCloudProvider()
    raise ValueError(f"Unknown WHATSAPP_PROVIDER: {provider!r}")

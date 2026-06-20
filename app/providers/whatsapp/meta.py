"""Meta WhatsApp Cloud API provider.

Sends approved templates (to start / re-engage) and free-form text (only valid
inside an open 24h window). Verify the API version and payload shape against the
current Meta Cloud API docs before going live.
"""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.providers.whatsapp.base import SendResult, WhatsAppProvider


class WhatsAppSendError(Exception):
    """Raised when the Meta Cloud API rejects or fails a send."""


class MetaCloudProvider(WhatsAppProvider):
    def __init__(self, client: httpx.Client | None = None) -> None:
        settings = get_settings()
        self._token = settings.meta_access_token
        self._phone_number_id = settings.meta_phone_number_id
        self._base_url = f"https://graph.facebook.com/{settings.meta_api_version}"
        self._client = client or httpx.Client(timeout=15.0)

    @staticmethod
    def _to(phone: str) -> str:
        # Meta expects the number without a leading "+".
        return phone.lstrip("+")

    def _post(self, payload: dict[str, object]) -> SendResult:
        url = f"{self._base_url}/{self._phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            response = self._client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise WhatsAppSendError(str(exc)) from exc
        if response.status_code >= 400:
            raise WhatsAppSendError(f"{response.status_code}: {response.text}")
        data = response.json()
        try:
            message_id = data["messages"][0]["id"]
        except (KeyError, IndexError, TypeError) as exc:
            raise WhatsAppSendError(f"unexpected response: {data}") from exc
        return SendResult(provider_message_id=message_id)

    def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        variables: list[str] | None = None,
    ) -> SendResult:
        components: list[dict[str, object]] = []
        if variables:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(v)} for v in variables],
                }
            )
        payload: dict[str, object] = {
            "messaging_product": "whatsapp",
            "to": self._to(to),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }
        return self._post(payload)

    def send_text(self, to: str, body: str) -> SendResult:
        payload: dict[str, object] = {
            "messaging_product": "whatsapp",
            "to": self._to(to),
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }
        return self._post(payload)

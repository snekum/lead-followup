import json

import httpx
import pytest

from app.providers.whatsapp.meta import MetaCloudProvider, WhatsAppSendError


def _provider(handler) -> MetaCloudProvider:
    return MetaCloudProvider(client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_send_template_success():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["to"] == "919876543210"  # leading + stripped
        assert body["template"]["name"] == "day0_thankyou"
        return httpx.Response(200, json={"messages": [{"id": "wamid.ABC"}]})

    result = _provider(handler).send_template(
        "+919876543210", "day0_thankyou", "en", ["Ravi", "Nexon"]
    )
    assert result.provider_message_id == "wamid.ABC"


def test_send_raises_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request")

    with pytest.raises(WhatsAppSendError):
        _provider(handler).send_text("+919876543210", "hello")

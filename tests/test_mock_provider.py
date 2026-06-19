from app.providers.whatsapp.mock import MockWhatsAppProvider


def test_send_text_records_outbox() -> None:
    provider = MockWhatsAppProvider()
    result = provider.send_text("+919999999999", "Hello!")

    assert result.provider_message_id.startswith("mock-")
    assert len(provider.outbox) == 1
    assert provider.outbox[0]["kind"] == "text"
    assert provider.outbox[0]["body"] == "Hello!"


def test_send_template_records_outbox() -> None:
    provider = MockWhatsAppProvider()
    result = provider.send_template(
        "+919999999999", "visit_followup", "en", ["Sneha", "Nexon"]
    )

    assert result.status == "sent"
    assert provider.outbox[0]["kind"] == "template"
    assert provider.outbox[0]["template"] == "visit_followup"
    assert provider.outbox[0]["variables"] == ["Sneha", "Nexon"]

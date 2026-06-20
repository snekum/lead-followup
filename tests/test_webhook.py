def test_verify_success(client):
    resp = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "saarthi-verify",
            "hub.challenge": "challenge-123",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "challenge-123"


def test_verify_bad_token(client):
    resp = client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
    )
    assert resp.status_code == 403


def test_inbound_reply_via_webhook(client):
    created = client.post("/leads", json={"name": "Ravi", "phone": "9876543210"})
    assert created.status_code == 201

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "type": "text",
                                    "text": {"body": "Yes!"},
                                    "id": "wamid.IN1",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    resp = client.post("/webhook/whatsapp", json=payload)
    assert resp.status_code == 200

    leads = client.get("/leads").json()
    assert leads[0]["status"] == "engaged"

def test_simulator_list(client):
    client.post("/leads", json={"name": "Ravi", "phone": "9876543210"})
    resp = client.get("/simulator")
    assert resp.status_code == 200
    assert "Ravi" in resp.text


def test_simulator_chat_page(client):
    lead_id = client.post("/leads", json={"name": "Asha", "phone": "9000000001"}).json()["id"]
    assert client.get(f"/simulator/{lead_id}").status_code == 200


def test_simulator_send_gets_assistant_reply(client):
    lead_id = client.post(
        "/leads",
        json={"name": "Vikram", "phone": "9000000002", "interested_model": "Nexon"},
    ).json()["id"]

    resp = client.post(
        f"/simulator/{lead_id}/send",
        data={"text": "Hi, I'm interested in the Nexon!"},
    )
    assert resp.status_code == 200  # redirect followed to the chat page

    page = client.get(f"/simulator/{lead_id}").text
    assert "interested in the Nexon" in page  # the customer's message
    assert "Sure, I can help" in page  # the fake assistant's reply

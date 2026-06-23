from app.db.models import Lead


def test_overview_renders(client):
    client.post(
        "/leads",
        json={"name": "Ravi Teja", "phone": "9876543210", "interested_model": "Nexon"},
    )
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Ravi Teja" in resp.text
    assert "Funnel" in resp.text


def test_lead_detail_renders(client):
    lead_id = client.post("/leads", json={"name": "Asha", "phone": "9000000001"}).json()["id"]
    resp = client.get(f"/dashboard/leads/{lead_id}")
    assert resp.status_code == 200
    assert "Asha" in resp.text


def test_lead_detail_404(client):
    assert client.get("/dashboard/leads/999999").status_code == 404


def test_handoff_page_renders(client):
    assert client.get("/dashboard/handoff").status_code == 200


def test_status_action(client):
    lead_id = client.post("/leads", json={"name": "Vikram", "phone": "9000000002"}).json()["id"]
    # NEW -> CONTACTED is a valid transition; TestClient follows the redirect.
    resp = client.post(f"/dashboard/leads/{lead_id}/status", data={"to": "contacted"})
    assert resp.status_code == 200
    assert "contacted" in client.get(f"/dashboard/leads/{lead_id}").text


def test_resolve_clears_open_question(client, db_session):
    lead_id = client.post("/leads", json={"name": "Query", "phone": "9000000003"}).json()["id"]
    lead = db_session.get(Lead, lead_id)
    lead.open_question = "what is the on-road price?"
    db_session.commit()

    client.post(f"/dashboard/leads/{lead_id}/resolve")

    db_session.expire_all()
    assert db_session.get(Lead, lead_id).open_question is None

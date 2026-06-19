def test_create_list_and_dedupe(client) -> None:
    resp = client.post(
        "/leads",
        json={"name": "Ravi", "phone": "9876543210", "interested_model": "Nexon"},
    )
    assert resp.status_code == 201
    assert resp.json()["phone"] == "+919876543210"

    # Same number in a different format => 409.
    dup = client.post("/leads", json={"name": "Ravi 2", "phone": "0098765 43210"})
    assert dup.status_code == 409

    bad = client.post("/leads", json={"name": "Bad", "phone": "12345"})
    assert bad.status_code == 422

    listing = client.get("/leads")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_import_endpoint(client) -> None:
    csv = (
        b"name,phone,model\n"
        b"Asha,9000000001,Punch\n"
        b"Asha Dup,9000000001,Punch\n"
        b"Kiran,9000000002,Tiago\n"
    )
    resp = client.post(
        "/leads/import",
        files={"file": ("leads.csv", csv, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["duplicates"] == 1

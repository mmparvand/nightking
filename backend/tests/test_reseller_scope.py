from app.models import ServiceProtocol


def test_reseller_scope_cannot_manage_other_resellers(client):
    # Login as reseller
    login_payload = {"username": "reseller", "password": "changeme", "role_tab": "RESELLER"}
    login_res = client.post("/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create user scoped to reseller (reseller_id should be enforced automatically)
    user_res = client.post(
        "/api/users",
        json={"email": "scoped@example.com", "full_name": "Scoped User", "reseller_id": None},
        headers=headers,
    )
    assert user_res.status_code == 201
    user_id = user_res.json()["id"]

    # Attempt to fetch users with pagination
    list_res = client.get("/api/users", headers=headers)
    assert list_res.status_code == 200
    assert any(u["id"] == user_id for u in list_res.json()["items"])

    # Create service scoped
    service_res = client.post(
        "/api/services",
        json={
            "name": "Scoped Service",
            "user_id": user_id,
            "reseller_id": None,
            "protocol": ServiceProtocol.XRAY_VLESS.value,
            "endpoint": "vpn.example.com:443",
        },
        headers=headers,
    )
    assert service_res.status_code == 201
    service_id = service_res.json()["id"]

    # Attempt to access non-existent service of other reseller
    other_res = client.get("/api/services/9999", headers=headers)
    assert other_res.status_code == 404

    # Cleanup
    client.delete(f"/api/services/{service_id}", headers=headers)
    client.delete(f"/api/users/{user_id}", headers=headers)

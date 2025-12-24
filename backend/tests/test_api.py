from app.models import ServiceProtocol


def test_user_and_service_crud(client):
    # Login as admin
    login_payload = {"username": "admin", "password": "changeme", "role_tab": "ADMIN"}
    login_res = client.post("/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create user
    user_payload = {"email": "user@example.com", "full_name": "Alice Admin", "reseller_id": None}
    user_res = client.post("/api/users", json=user_payload, headers=headers)
    assert user_res.status_code == 201
    user_id = user_res.json()["id"]

    # List users
    list_res = client.get("/api/users", headers=headers)
    assert list_res.status_code == 200
    assert any(u["id"] == user_id for u in list_res.json()["items"])

    # Update user
    update_res = client.put(
        f"/api/users/{user_id}",
        json={"email": "user2@example.com", "full_name": "Alice Updated"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["email"] == "user2@example.com"

    # Create service
    service_payload = {
        "name": "Core VPN",
        "user_id": user_id,
        "reseller_id": None,
        "protocol": ServiceProtocol.XRAY_VLESS.value,
        "endpoint": "vpn.example.com:443",
    }
    service_res = client.post("/api/services", json=service_payload, headers=headers)
    assert service_res.status_code == 201
    service_id = service_res.json()["id"]

    # Token generation
    token_res = client.post(f"/api/services/{service_id}/token", headers=headers)
    assert token_res.status_code == 200
    assert token_res.json()["service_id"] == service_id

    # Update service
    update_service_res = client.put(
        f"/api/services/{service_id}",
        json={"name": "Core VPN Updated", "protocol": ServiceProtocol.XRAY_VLESS.value, "endpoint": "vpn.example.com:8443"},
        headers=headers,
    )
    assert update_service_res.status_code == 200
    assert update_service_res.json()["name"] == "Core VPN Updated"

    # List services
    services_list = client.get("/api/services", headers=headers)
    assert services_list.status_code == 200
    assert any(s["id"] == service_id for s in services_list.json()["items"])

    # Delete service
    del_res = client.delete(f"/api/services/{service_id}", headers=headers)
    assert del_res.status_code == 204

    # Delete user
    del_user = client.delete(f"/api/users/{user_id}", headers=headers)
    assert del_user.status_code == 204

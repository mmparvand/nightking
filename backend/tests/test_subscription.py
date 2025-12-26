from app.models import ServiceProtocol


def _auth_headers(client):
    login_payload = {"username": "admin", "password": "changeme", "role_tab": "ADMIN"}
    login_res = client.post("/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_subscription_payload_and_qr(client):
    headers = _auth_headers(client)

    # Create a user
    user_payload = {"email": "sub@example.com", "full_name": "Subscription User", "reseller_id": None}
    user_res = client.post("/api/users", json=user_payload, headers=headers)
    assert user_res.status_code == 201
    user_id = user_res.json()["id"]

    # Create a service
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

    # Ensure token exists
    token_res = client.post(f"/api/services/{service_id}/token", headers=headers)
    assert token_res.status_code == 200
    token_value = token_res.json()["token"]

    # Subscription payload
    sub_res = client.get(f"/sub/{token_value}")
    assert sub_res.status_code == 200
    payload_text = sub_res.text
    assert payload_text.startswith("vless://")
    assert token_value in payload_text

    # QR endpoint
    qr_res = client.get(f"/sub/{token_value}/qr")
    assert qr_res.status_code == 200
    assert qr_res.headers["content-type"].startswith("image/png")
    assert qr_res.content  # non-empty

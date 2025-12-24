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


def test_subscription_respects_inactive_and_expired(client, monkeypatch):
    headers = _auth_headers(client)
    login_res = client.post("/auth/login", json={"username": "admin", "password": "changeme", "role_tab": "ADMIN"})
    assert login_res.status_code == 200

    # Create a user
    user_res = client.post("/api/users", json={"email": "expire@example.com", "full_name": "Expire User"}, headers=headers)
    assert user_res.status_code == 201
    user_id = user_res.json()["id"]

    # Create inactive service
    service_payload = {
        "name": "Inactive",
        "user_id": user_id,
        "reseller_id": None,
        "protocol": ServiceProtocol.XRAY_VLESS.value,
        "endpoint": "vpn.example.com:443",
        "is_active": False,
    }
    service_res = client.post("/api/services", json=service_payload, headers=headers)
    assert service_res.status_code == 201
    service_id = service_res.json()["id"]
    token_res = client.post(f"/api/services/{service_id}/token", headers=headers)
    token = token_res.json()["token"]
    sub_res = client.get(f"/sub/{token}")
    assert sub_res.status_code == 403
    assert "DISABLED" in sub_res.text

    # Expired service
    service_payload["name"] = "Expired"
    service_payload["is_active"] = True
    service_payload["expires_at"] = "2000-01-01T00:00:00Z"
    exp_service = client.post("/api/services", json=service_payload, headers=headers)
    token_res2 = client.post(f"/api/services/{exp_service.json()['id']}/token", headers=headers)
    token2 = token_res2.json()["token"]
    sub_res2 = client.get(f"/sub/{token2}")
    assert sub_res2.status_code == 403
    assert "EXPIRED" in sub_res2.text

    # Traffic exceeded
    service_payload["name"] = "Traffic Limited"
    service_payload["traffic_limit_bytes"] = 1
    service_payload["traffic_used_bytes"] = 2
    tl_service = client.post("/api/services", json=service_payload, headers=headers)
    tl_token = client.post(f"/api/services/{tl_service.json()['id']}/token", headers=headers).json()["token"]
    sub_res3 = client.get(f"/sub/{tl_token}")
    assert sub_res3.status_code == 403
    assert "TRAFFIC" in sub_res3.text


def test_subscription_ip_limit(client, monkeypatch):
    headers = _auth_headers(client)

    class FakeRedis:
        def __init__(self):
            self.store = {}

        def sadd(self, key, value):
            self.store.setdefault(key, set()).add(value)

        def scard(self, key):
            return len(self.store.get(key, set()))

        def expire(self, key, ttl):
            return True

        def get(self, key):
            return self.store.get(key, 0)

        def incr(self, key):
            self.store[key] = int(self.store.get(key, 0)) + 1

    fake = FakeRedis()
    from app import subscription

    monkeypatch.setattr(subscription, "get_redis", lambda: fake)

    # user and service
    user_res = client.post("/api/users", json={"email": "limit@example.com", "full_name": "Limit User"}, headers=headers)
    user_id = user_res.json()["id"]
    service_payload = {
        "name": "Limited",
        "user_id": user_id,
        "reseller_id": None,
        "protocol": ServiceProtocol.XRAY_VLESS.value,
        "endpoint": "vpn.example.com:443",
        "ip_limit": 1,
    }
    service_res = client.post("/api/services", json=service_payload, headers=headers)
    service_id = service_res.json()["id"]
    token_res = client.post(f"/api/services/{service_id}/token", headers=headers)
    token = token_res.json()["token"]

    # First IP allowed
    sub_res = client.get(f"/sub/{token}", headers={"X-Forwarded-For": "1.1.1.1"})
    assert sub_res.status_code == 200
    # Second unique IP blocked
    sub_res2 = client.get(f"/sub/{token}", headers={"X-Forwarded-For": "2.2.2.2"})
    assert sub_res2.status_code == 403

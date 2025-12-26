import os
from pathlib import Path

from app.config import get_settings
from app.models import ServiceProtocol


def _auth_headers(client):
    login_payload = {"username": "admin", "password": "changeme", "role_tab": "ADMIN"}
    login_res = client.post("/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_xray_render_and_apply(client, monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("XRAY_CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setenv("XRAY_RELOAD_COMMAND", "")
    monkeypatch.setenv("XRAY_STATUS_HOST", "localhost")
    headers = _auth_headers(client)

    # Seed service
    user_payload = {"email": "xray@example.com", "full_name": "X Ray", "reseller_id": None}
    user_res = client.post("/api/users", json=user_payload, headers=headers)
    assert user_res.status_code == 201
    user_id = user_res.json()["id"]

    service_payload = {
        "name": "Xray VPN",
        "user_id": user_id,
        "reseller_id": None,
        "protocol": ServiceProtocol.XRAY_VLESS.value,
        "endpoint": "vpn.example.com:8443",
    }
    service_res = client.post("/api/services", json=service_payload, headers=headers)
    assert service_res.status_code == 201

    render_res = client.post("/xray/render", headers=headers)
    assert render_res.status_code == 200
    render_json = render_res.json()
    assert "config" in render_json
    assert render_json["config"]["inbounds"][0]["protocol"] == "vless"

    apply_res = client.post("/xray/apply", headers=headers)
    assert apply_res.status_code == 200
    config_path = Path(os.environ["XRAY_CONFIG_PATH"])
    assert config_path.exists()
    assert config_path.read_text()

    status_res = client.get("/xray/status", headers=headers)
    assert status_res.status_code == 200
    status_json = status_res.json()
    assert "healthy" in status_json
    assert status_json["last_apply_status"] is not None

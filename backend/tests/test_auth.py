from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_and_me_round_trip() -> None:
    login_payload = {"username": "admin", "password": "changeme", "role_tab": "ADMIN"}
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"
    token = data["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me = me_response.json()
    assert me["username"] == "admin"
    assert me["role"] == "ADMIN"


def test_login_rejects_wrong_role() -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "changeme", "role_tab": "RESELLER"})
    assert response.status_code == 401


def test_me_requires_token(client) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401

import time

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from api.auth import current_user_id

SECRET = "segredo-de-teste"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CHAT_JWT_SECRET", SECRET)
    monkeypatch.setenv("CHAT_AUTH_REQUIRED", "true")
    app = FastAPI()

    @app.get("/quem")
    def quem(uid=Depends(current_user_id)):
        return {"uid": uid}

    return TestClient(app)


def _token(**over):
    claims = {"sub": "u1", "exp": int(time.time()) + 60, **over}
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, SECRET, algorithm="HS256")


def test_valid_token_returns_user_id(client):
    r = client.get("/quem", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 200 and r.json() == {"uid": "u1"}


def test_missing_token_is_401(client):
    assert client.get("/quem").status_code == 401


def test_expired_token_is_401(client):
    r = client.get("/quem", headers={"Authorization": f"Bearer {_token(exp=int(time.time()) - 5)}"})
    assert r.status_code == 401


def test_wrong_signature_is_401(client):
    bad = jwt.encode({"sub": "u1", "exp": int(time.time()) + 60}, "outro", algorithm="HS256")
    assert client.get("/quem", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_token_without_sub_is_401(client):
    assert client.get("/quem", headers={"Authorization": f"Bearer {_token(sub=None)}"}).status_code == 401


def test_auth_can_be_disabled_for_local_dev(client, monkeypatch):
    monkeypatch.setenv("CHAT_AUTH_REQUIRED", "false")
    r = client.get("/quem")
    assert r.status_code == 200 and r.json() == {"uid": None}

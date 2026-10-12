import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import current_user_id
from api.routers import chat

SID = "11111111-1111-1111-1111-111111111111"
MID = "22222222-2222-2222-2222-222222222222"


class FakeRepo:
    def __init__(self, owns=True):
        self.owns = owns
        self.feedback = []

    async def claim_session(self, session_id, user_id):
        return self.owns

    async def message_belongs_to(self, message_id, user_id):
        return self.owns

    async def save_message_feedback(self, message_id, feedback):
        self.feedback.append((message_id, feedback))


class FakeAgent:
    async def stream_events(self, session_id, message):
        yield {"type": "token", "content": "oi"}


def _client(monkeypatch, owns=True, user="u1"):
    repo = FakeRepo(owns)
    monkeypatch.setattr(chat, "_postgres_chat_adapter", repo)
    app = FastAPI()
    app.include_router(chat.router)
    app.dependency_overrides[current_user_id] = lambda: user
    app.dependency_overrides[chat.get_chat_agent] = lambda: FakeAgent()
    return TestClient(app), repo


def test_owner_can_stream(monkeypatch):
    c, _ = _client(monkeypatch)
    r = c.post(f"/chat/{SID}", json={"user_message": "oi"})
    assert r.status_code == 200 and '"token"' in r.text


def test_other_users_session_is_403(monkeypatch):
    c, _ = _client(monkeypatch, owns=False)
    assert c.post(f"/chat/{SID}", json={"user_message": "oi"}).status_code == 403


def test_invalid_session_id_is_400(monkeypatch):
    c, _ = _client(monkeypatch)
    assert c.post("/chat/nao-e-uuid", json={"user_message": "oi"}).status_code == 400


def test_feedback_on_foreign_message_is_403_and_not_saved(monkeypatch):
    c, repo = _client(monkeypatch, owns=False)
    assert c.post(f"/chat/message/{MID}/feedback", json={"feedback": "like"}).status_code == 403
    assert repo.feedback == []


def test_without_auth_no_ownership_check(monkeypatch):
    c, repo = _client(monkeypatch, owns=False, user=None)
    assert c.post(f"/chat/{SID}", json={"user_message": "oi"}).status_code == 200
    assert c.post(f"/chat/message/{MID}/feedback", json={"feedback": "like"}).status_code == 200
    assert repo.feedback == [(MID, "like")]

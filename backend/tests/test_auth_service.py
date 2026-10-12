import asyncio

import pytest

from core.application.auth_service import AuthError, AuthService, hash_password, verify_password
from ports.user_port import EmailAlreadyRegistered, UserRecord, UserRepositoryPort


class FakeUsers(UserRepositoryPort):
    def __init__(self):
        self.by_email = {}

    async def create(self, nome, email, senha_hash):
        if email in self.by_email:
            raise EmailAlreadyRegistered(email)
        self.by_email[email] = UserRecord(f"id-{len(self.by_email)}", nome, email, senha_hash)
        return self.by_email[email]

    async def get_by_email(self, email):
        return self.by_email.get(email)

    async def get_by_id(self, user_id):
        return next((u for u in self.by_email.values() if u.id == user_id), None)


def run(coro):
    return asyncio.run(coro)


def test_hash_is_salted_and_verifiable():
    a, b = hash_password("senha-forte-1"), hash_password("senha-forte-1")
    assert a != b and verify_password("senha-forte-1", a) and not verify_password("outra", a)
    assert not verify_password("x", "lixo")


def test_register_normalizes_email_and_never_stores_plain_password():
    users = FakeUsers()
    u = run(AuthService(users).register("  Ana ", " Ana@Ex.com ", "senha-forte-1"))
    assert (u.nome, u.email) == ("Ana", "ana@ex.com") and "senha-forte-1" not in u.senha_hash


@pytest.mark.parametrize("nome,email,senha", [("", "a@b.co", "senha-forte-1"), ("A", "sem-arroba", "senha-forte-1"), ("A", "a@b.co", "curta")])
def test_register_rejects_invalid_input(nome, email, senha):
    with pytest.raises(AuthError):
        run(AuthService(FakeUsers()).register(nome, email, senha))


def test_register_rejects_duplicate_email():
    svc = AuthService(FakeUsers())
    run(svc.register("Ana", "a@b.co", "senha-forte-1"))
    with pytest.raises(AuthError, match="já está cadastrado"):
        run(svc.register("Outra", "A@B.co", "senha-forte-2"))


def test_login_ok_and_same_message_for_unknown_email_and_wrong_password():
    svc = AuthService(FakeUsers())
    run(svc.register("Ana", "a@b.co", "senha-forte-1"))
    assert run(svc.login("A@b.co", "senha-forte-1")).email == "a@b.co"
    msgs = set()
    for email, senha in [("a@b.co", "errada-123"), ("x@y.co", "senha-forte-1")]:
        with pytest.raises(AuthError) as e:
            run(svc.login(email, senha))
        msgs.add(str(e.value))
    assert len(msgs) == 1

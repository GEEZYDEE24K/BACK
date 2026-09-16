import pytest
from backend_estudiantil.domain.services.user_service import UserService
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.schemas.user import UserCreate, UserUpdate
import uuid
from datetime import datetime

class InMemoryUserRepository:
    """Simple in‑memory repo used for unit testing the service."""
    def __init__(self):
        self.store = {}

    async def get_by_id(self, user_id: str):
        return self.store.get(user_id)

    async def get_by_email(self, email: str):
        return next((u for u in self.store.values() if u.email == email), None)

    async def create(self, user: User):
        self.store[user.id] = user
        return user

    async def update(self, user: User):
        self.store[user.id] = user
        return user

    async def delete(self, user_id: str):
        self.store.pop(user_id, None)

@pytest.fixture
def repo():
    return InMemoryUserRepository()

@pytest.fixture
def service(repo):
    return UserService(repo)

@pytest.mark.asyncio
async def test_create_user(service):
    payload = UserCreate(email="test@example.com", password="secret123", name="Tester")
    user = await service.create_user(payload)
    assert user.id is not None
    assert user.email == payload.email
    assert user.name == payload.name
    # Password should be stored hashed
    assert user.hashed_password != payload.password

@pytest.mark.asyncio
async def test_get_user(service):
    payload = UserCreate(email="bob@example.com", password="pwd", name="Bob")
    created = await service.create_user(payload)
    fetched = await service.get_user(created.id)
    assert fetched.id == created.id
    assert fetched.email == created.email

@pytest.mark.asyncio
async def test_update_user(service):
    payload = UserCreate(email="alice@example.com", password="pwd", name="Alice")
    user = await service.create_user(payload)
    update_payload = UserUpdate(name="Alice Updated")
    updated = await service.update_user(user.id, update_payload)
    assert updated.name == "Alice Updated"

@pytest.mark.asyncio
async def test_delete_user(service):
    payload = UserCreate(email="del@example.com", password="pwd", name="Del")
    user = await service.create_user(payload)
    await service.delete_user(user.id)
    with pytest.raises(ValueError):
        await service.get_user(user.id)

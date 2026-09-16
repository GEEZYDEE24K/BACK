from datetime import datetime
import uuid
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.schemas.user import UserCreate, UserUpdate

class UserService:
    """Domain service handling business logic for users."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create_user(self, payload: UserCreate) -> User:
        # Check if email already exists
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise ValueError("Email already registered")
        # Normally we would hash the password; placeholder here
        hashed_password = self._hash_password(payload.password)
        hashed_password = self._hash_password(payload.password)
        user = User(
            id=str(uuid.uuid4()),
            email=payload.email,
            hashed_password=hashed_password,
            name=payload.name,
            role=payload.role or "user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return await self.repo.create(user)

    async def get_user(self, user_id: str) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    async def update_user(self, user_id: str, payload: UserUpdate) -> User:
        user = await self.get_user(user_id)
        if payload.email and payload.email != user.email:
            # ensure new email not taken
            if await self.repo.get_by_email(payload.email):
                raise ValueError("Email already taken")
            user.email = payload.email
        if payload.name is not None:
            user.name = payload.name
        # password change optional
        if payload.password:
            user.hashed_password = self._hash_password(payload.password)
        user.updated_at = datetime.utcnow()
        return await self.repo.update(user)

    async def delete_user(self, user_id: str) -> None:
        await self.repo.delete(user_id)

    def _hash_password(self, password: str) -> str:
        # Simple placeholder using sha256; replace with bcrypt in production
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

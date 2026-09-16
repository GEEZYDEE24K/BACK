import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend_estudiantil.config.settings import settings

# Async engine and session factory
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# SQLAlchemy User model
class UserORM(Base):
    __tablename__ = "usuarios"
    id = sa.Column(sa.String, primary_key=True, index=True)
    email = sa.Column(sa.String, unique=True, nullable=False, index=True)
    hashed_password = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=True)
    created_at = sa.Column(sa.DateTime, default=sa.func.utcnow())
    role = sa.Column(sa.String, default="user", nullable=False)

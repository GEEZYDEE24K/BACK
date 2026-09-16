from datetime import datetime
from typing import Optional

class User:
    """Domain entity representing a user.

    Attributes:
        id: Unique identifier (UUID string).
        email: User's email address.
        hashed_password: Password hash (never store plain). 
        name: Optional full name.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    def __init__(
        self,
        id: str,
        email: str,
        hashed_password: str,
        name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        role: str = "user",
    ) -> None:
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.name = name
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.role = role

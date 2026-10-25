from abc import ABC, abstractmethod
from typing import Any, Dict

class Authenticator(ABC):
    """Port (interface) for authentication token handling."""

    @abstractmethod
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a signed access token from payload data."""
        ...

    @abstractmethod
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a signed refresh token from payload data."""
        ...

    @abstractmethod
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode a token, returning its payload."""
        ...

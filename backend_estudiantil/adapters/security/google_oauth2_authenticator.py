import httpx
from fastapi import HTTPException, status
from urllib.parse import urlencode
from backend_estudiantil.config.settings import settings

class GoogleOAuth2Authenticator:
    """Handles the Google OAuth2 flow.

    - ``get_authorization_url`` builds the URL the client should be redirected to.
    - ``exchange_code`` exchanges an authorization ``code`` for an access token.
    - ``get_userinfo`` fetches the user profile using the access token.
    """

    async def get_authorization_url(self) -> str:
        """Return the Google consent screen URL.

        Uses ``settings.GOOGLE_CLIENT_ID``, ``settings.GOOGLE_REDIRECT_URI`` and
        ``settings.GOOGLE_SCOPES`` (defaults to ``openid email profile``).
        """
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": getattr(settings, "GOOGLE_SCOPES", "openid email profile"),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange the authorization ``code`` for tokens.

        Returns the JSON payload from Google which contains ``access_token``
        (and optionally ``refresh_token`` and ``id_token``).
        """
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange code for token")
        return resp.json()

    async def get_userinfo(self, access_token: str) -> dict:
        """Fetch the user's profile from Google.

        The endpoint returns fields such as ``email``, ``name`` and ``id``.
        """
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        async with httpx.AsyncClient() as client:
            resp = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user info from Google")
        return resp.json()

import httpx
from fastapi import HTTPException, status
from urllib.parse import urlencode
from backend_estudiantil.config.settings import settings

class FacebookOAuth2Authenticator:
    async def get_authorization_url(self) -> str:
        params = {
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
            "scope": getattr(settings, "FACEBOOK_SCOPES", "email,public_profile"),
            "response_type": "code",
        }
        return f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "client_secret": settings.FACEBOOK_CLIENT_SECRET,
            "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
            "code": code,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(token_url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange Facebook code")
        return resp.json()

    async def get_userinfo(self, access_token: str) -> dict:
        userinfo_url = "https://graph.facebook.com/me"
        params = {
            "fields": "id,name,email",
            "access_token": access_token
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(userinfo_url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch Facebook user info")
        return resp.json()

"""
Google OAuth 2.0 Handler with PKCE
"""
import httpx
from urllib.parse import urlencode
from typing import Dict


class GoogleOAuthHandler:
    """Handles Google OAuth 2.0 flow with PKCE"""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.google_oauth_base = "https://accounts.google.com/o/oauth2/v2/auth"
        self.google_token_url = "https://oauth2.googleapis.com/token"
        self.google_userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"

    def get_authorization_url(self, state: str, code_challenge: str) -> str:
        """
        Generate Google OAuth authorization URL with PKCE

        Args:
            state: CSRF protection state parameter
            code_challenge: PKCE code challenge

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        return f"{self.google_oauth_base}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, code_verifier: str) -> Dict:
        """
        Exchange authorization code for access tokens

        Args:
            code: Authorization code from Google
            code_verifier: PKCE code verifier

        Returns:
            Token response from Google

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.google_token_url, data=data)
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, google_access_token: str) -> Dict:
        """
        Get user information from Google

        Args:
            google_access_token: Access token from Google

        Returns:
            User information (email, name, picture)

        Raises:
            httpx.HTTPStatusError: If user info request fails
        """
        headers = {"Authorization": f"Bearer {google_access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(self.google_userinfo_url, headers=headers)
            response.raise_for_status()
            return response.json()

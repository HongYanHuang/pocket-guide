"""
Google OAuth 2.0 Handler with PKCE
Supports multiple OAuth clients (web, iOS, Android)
"""
import httpx
from urllib.parse import urlencode
from typing import Dict, Optional
from google.oauth2 import id_token
from google.auth.transport import requests


class GoogleOAuthHandler:
    """Handles Google OAuth 2.0 flow with PKCE for multiple client types"""

    def __init__(self, clients: Dict[str, Dict[str, str]], default_redirect_uri: str = None):
        """
        Initialize OAuth handler with multiple client configurations

        Args:
            clients: Dict of client configs, e.g.:
                {
                    "web": {"client_id": "...", "client_secret": "..."},
                    "ios": {"client_id": "..."}  # iOS has no client_secret
                }
            default_redirect_uri: Optional default redirect URI (for backward compatibility)
        """
        self.clients = clients
        self.default_redirect_uri = default_redirect_uri
        self.google_oauth_base = "https://accounts.google.com/o/oauth2/v2/auth"
        self.google_token_url = "https://oauth2.googleapis.com/token"
        self.google_userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"

        # Legacy support: if clients is empty, create web client from old format
        if not self.clients:
            self.clients = {"web": {}}

    def detect_client_type(self, redirect_uri: str) -> str:
        """
        Auto-detect client type from redirect URI

        Args:
            redirect_uri: The OAuth redirect URI

        Returns:
            Client type: "ios", "android", or "web"
        """
        if redirect_uri.startswith("pocketguide://"):
            return "ios"
        elif redirect_uri.startswith("http://") or redirect_uri.startswith("https://"):
            return "web"
        else:
            return "web"  # Default to web

    def get_client_config(self, client_type: str = "web") -> Dict[str, str]:
        """
        Get client configuration by type

        Args:
            client_type: Type of client (web, ios, android)

        Returns:
            Client configuration dict

        Raises:
            ValueError: If client type not configured
        """
        if client_type not in self.clients:
            raise ValueError(f"Client type '{client_type}' not configured. Available: {list(self.clients.keys())}")
        return self.clients[client_type]

    def get_authorization_url(self, state: str, code_challenge: str, redirect_uri: str = None, client_type: str = None) -> str:
        """
        Generate Google OAuth authorization URL with PKCE

        Args:
            state: CSRF protection state parameter
            code_challenge: PKCE code challenge
            redirect_uri: Optional redirect URI (defaults to self.default_redirect_uri)
            client_type: Optional client type (auto-detected from redirect_uri if not provided)

        Returns:
            Authorization URL to redirect user to
        """
        redirect_uri = redirect_uri or self.default_redirect_uri

        # Auto-detect client type if not provided
        if client_type is None and redirect_uri:
            client_type = self.detect_client_type(redirect_uri)
        elif client_type is None:
            client_type = "web"

        # Get client config
        client_config = self.get_client_config(client_type)

        params = {
            "client_id": client_config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        return f"{self.google_oauth_base}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, code_verifier: str, redirect_uri: str = None, client_type: str = None) -> Dict:
        """
        Exchange authorization code for access tokens

        Args:
            code: Authorization code from Google
            code_verifier: PKCE code verifier
            redirect_uri: Optional redirect URI (defaults to self.default_redirect_uri)
            client_type: Optional client type (auto-detected from redirect_uri if not provided)

        Returns:
            Token response from Google

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        redirect_uri = redirect_uri or self.default_redirect_uri

        # Auto-detect client type if not provided
        if client_type is None and redirect_uri:
            client_type = self.detect_client_type(redirect_uri)
        elif client_type is None:
            client_type = "web"

        # Get client config
        client_config = self.get_client_config(client_type)

        data = {
            "client_id": client_config["client_id"],
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }

        # Only add client_secret if it exists (iOS doesn't have it)
        if "client_secret" in client_config and client_config["client_secret"]:
            data["client_secret"] = client_config["client_secret"]

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

    def verify_id_token(self, token: str, client_type: str = "ios") -> Dict:
        """
        Verify Google ID token from native SDK using official google-auth library

        This method uses Google's official library which:
        - Verifies token signature cryptographically (no API call needed)
        - Caches Google's public keys for performance
        - Has no rate limits (local verification)
        - Is more secure and robust

        Args:
            token: ID token from Google Sign-In SDK
            client_type: Client type to verify against (ios, android, web)

        Returns:
            User information from verified token (email, name, picture, sub)

        Raises:
            ValueError: If token is invalid, expired, or client_id doesn't match
        """
        # Get expected client config
        client_config = self.get_client_config(client_type)
        expected_client_id = client_config["client_id"]

        try:
            # Verify the ID token with Google's official library
            # This verifies the signature cryptographically using Google's public keys
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                expected_client_id
            )

            # Double-check audience matches (redundant but explicit)
            if idinfo.get('aud') != expected_client_id:
                raise ValueError(
                    f"Invalid client_id. Expected {expected_client_id}, got {idinfo.get('aud')}"
                )

            # Return user info in standardized format
            return {
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
                "sub": idinfo.get("sub"),  # Google user ID
                "email_verified": idinfo.get("email_verified", False)
            }

        except ValueError as e:
            # google-auth raises ValueError for invalid tokens
            raise ValueError(f"Token verification failed: {str(e)}")

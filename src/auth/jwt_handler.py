"""
JWT Token Handler for authentication
"""
from datetime import datetime, timedelta
import jwt
from typing import Dict, Tuple


class JWTHandler:
    """Handles JWT token creation and validation"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 15

    def create_access_token(self, user_data: dict) -> str:
        """
        Create a JWT access token

        Args:
            user_data: User information (email, name, role, scopes, etc.)

        Returns:
            JWT token string
        """
        payload = {
            "sub": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "role": user_data.get("role", "client_user"),
            "scopes": user_data.get("scopes", []),
            "client_type": user_data.get("client_type", "backstage"),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def validate_token(self, token: str) -> Tuple[bool, Dict]:
        """
        Validate a JWT token

        Args:
            token: JWT token string

        Returns:
            Tuple of (is_valid, payload_or_error)
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return (True, payload)
        except jwt.ExpiredSignatureError:
            return (False, {"error": "Token expired"})
        except jwt.InvalidTokenError:
            return (False, {"error": "Invalid token"})

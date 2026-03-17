"""
Session Manager for refresh token storage
"""
from datetime import datetime, timedelta
import uuid
from typing import Optional, Dict
import threading


class SessionManager:
    """Manages user sessions with refresh tokens"""

    def __init__(self, refresh_token_expire_days: int = 7):
        self.sessions: Dict[str, dict] = {}
        self.lock = threading.Lock()
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_session(self, user_data: dict) -> str:
        """
        Create a new session and return refresh token

        Args:
            user_data: User information to store in session

        Returns:
            Refresh token (UUID string)
        """
        refresh_token = str(uuid.uuid4())
        with self.lock:
            self.sessions[refresh_token] = {
                "user": user_data,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
                "last_accessed": datetime.utcnow()
            }
        return refresh_token

    def get_session(self, refresh_token: str) -> Optional[dict]:
        """
        Get session data for a refresh token

        Args:
            refresh_token: Refresh token to look up

        Returns:
            Session data if valid, None if expired or not found
        """
        with self.lock:
            session = self.sessions.get(refresh_token)
            if not session:
                return None

            # Check expiration
            if datetime.utcnow() > session["expires_at"]:
                del self.sessions[refresh_token]
                return None

            # Update last accessed time
            session["last_accessed"] = datetime.utcnow()
            return session

    def delete_session(self, refresh_token: str):
        """
        Delete a session (logout)

        Args:
            refresh_token: Refresh token to delete
        """
        with self.lock:
            if refresh_token in self.sessions:
                del self.sessions[refresh_token]

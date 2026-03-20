"""
Authentication API Router
Handles Google OAuth flow, token refresh, and logout
"""
from fastapi import APIRouter, HTTPException, Depends
from api_models import AuthTokenResponse, UserInfo, RefreshTokenRequest
from auth.dependencies import get_current_user
import uuid
import logging
from typing import Dict

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

# Store OAuth states temporarily (in production, use Redis)
oauth_states: Dict[str, dict] = {}


@router.get("/google/login")
async def google_login(redirect_uri: str, code_challenge: str):
    """
    Initiate Google OAuth login

    Args:
        redirect_uri: Frontend callback URL
        code_challenge: PKCE code challenge (SHA256 of verifier)

    Returns:
        Authorization URL and state parameter
    """
    from api_server import oauth_handler

    state = str(uuid.uuid4())
    oauth_states[state] = {"redirect_uri": redirect_uri}

    auth_url = oauth_handler.get_authorization_url(state, code_challenge, redirect_uri)
    return {"auth_url": auth_url, "state": state}


@router.get("/google/callback", response_model=AuthTokenResponse)
async def google_callback(code: str, state: str, code_verifier: str):
    """
    Handle Google OAuth callback

    Args:
        code: Authorization code from Google
        state: CSRF protection state parameter
        code_verifier: PKCE code verifier

    Returns:
        JWT access token and refresh token

    Raises:
        HTTPException: If OAuth fails or user not authorized
    """
    from api_server import oauth_handler, jwt_handler, session_manager, config

    # Validate state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    state_data = oauth_states.pop(state)
    redirect_uri = state_data.get("redirect_uri")

    # Exchange code for tokens
    try:
        google_tokens = await oauth_handler.exchange_code_for_tokens(code, code_verifier, redirect_uri)
        user_info = await oauth_handler.get_user_info(google_tokens["access_token"])
    except Exception as e:
        logger.error(f"OAuth failed: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

    # Determine client type from redirect_uri
    auth_config = config.get("authentication", {})
    user_roles_config = auth_config.get("user_roles", {})

    # Detect which app the user is logging in from
    client_type = "client_app"  # default
    if redirect_uri and ("5173" in redirect_uri or "backstage" in redirect_uri.lower()):
        client_type = "backstage"

    logger.info(f"Login attempt from {client_type} app (redirect_uri: {redirect_uri})")

    # Role assignment based on client type
    if client_type == "backstage":
        # Backstage login - only allow whitelisted users
        if user_info["email"] not in user_roles_config:
            raise HTTPException(
                status_code=403,
                detail="Not authorized for backstage access. Please contact administrator."
            )

        # Assign configured backstage role
        user_config = user_roles_config[user_info["email"]]
        user_data = {
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture"),
            "role": user_config["role"],
            "scopes": user_config["scopes"],
            "client_type": "backstage"
        }
        logger.info(f"Backstage login: {user_info['email']} as {user_config['role']}")

    else:
        # Client app login - assign client_user role to everyone
        # Even if user is in backstage config, they get client_user for client app
        allow_public = auth_config.get("allow_public_signup", False)

        if not allow_public:
            raise HTTPException(
                status_code=403,
                detail="Client app registration is currently disabled. Please contact administrator."
            )

        user_data = {
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture"),
            "role": auth_config.get("default_role", "client_user"),
            "scopes": auth_config.get("default_scopes", ["client_app", "read_tours", "user_data"]),
            "client_type": "client_app"
        }
        logger.info(f"Client app login: {user_info['email']} as client_user")

    # Create session and tokens
    refresh_token = session_manager.create_session(user_data)
    access_token = jwt_handler.create_access_token(user_data)

    logger.info(f"User {user_info['email']} logged in with role {user_data['role']}")

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    Args:
        request: Refresh token request

    Returns:
        New access token (same refresh token)

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    from api_server import session_manager, jwt_handler

    session = session_manager.get_session(request.refresh_token)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    access_token = jwt_handler.create_access_token(session["user"])

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token
    )


@router.post("/logout")
async def logout(request: RefreshTokenRequest, current_user: Dict = Depends(get_current_user)):
    """
    Logout user and invalidate session

    Args:
        request: Refresh token to invalidate
        current_user: Current user from JWT token

    Returns:
        Success message
    """
    from api_server import session_manager

    session_manager.delete_session(request.refresh_token)
    logger.info(f"User {current_user['email']} logged out")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: Dict = Depends(get_current_user)):
    """
    Get current user information

    Args:
        current_user: Current user from JWT token

    Returns:
        User information
    """
    return UserInfo(**current_user)

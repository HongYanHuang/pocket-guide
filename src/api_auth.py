"""
Authentication API Router
Handles Google OAuth flow, token refresh, and logout
"""
from fastapi import APIRouter, HTTPException, Depends
from api_models import AuthTokenResponse, UserInfo, RefreshTokenRequest, IDTokenVerifyRequest
from auth.dependencies import get_current_user
import uuid
import logging
from typing import Dict

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

# Store OAuth states temporarily (in production, use Redis)
# Format: { state: { redirect_uri: str, client_type: str, oauth_client_type: str } }
# client_type: "backstage" or "client_app" (application context)
# oauth_client_type: "web" or "ios" (OAuth client type)
oauth_states: Dict[str, dict] = {}


@router.get("/backstage/google/login")
async def backstage_google_login(redirect_uri: str, code_challenge: str):
    """
    Initiate Google OAuth login for BACKSTAGE admin panel

    Args:
        redirect_uri: Backstage callback URL
        code_challenge: PKCE code challenge (SHA256 of verifier)

    Returns:
        Authorization URL and state parameter
    """
    from api_server import oauth_handler

    # Backstage always uses web client
    oauth_client_type = "web"

    state = str(uuid.uuid4())
    oauth_states[state] = {
        "redirect_uri": redirect_uri,
        "client_type": "backstage",
        "oauth_client_type": oauth_client_type
    }

    auth_url = oauth_handler.get_authorization_url(state, code_challenge, redirect_uri, oauth_client_type)
    logger.info(f"Backstage login initiated for {redirect_uri} (OAuth client: {oauth_client_type})")
    return {"auth_url": auth_url, "state": state}


@router.get("/client/google/login")
async def client_google_login(redirect_uri: str, code_challenge: str):
    """
    Initiate Google OAuth login for CLIENT APP

    Args:
        redirect_uri: Client app callback URL (web or mobile)
        code_challenge: PKCE code challenge (SHA256 of verifier)

    Returns:
        Authorization URL and state parameter
    """
    from api_server import oauth_handler

    # Auto-detect OAuth client type from redirect URI
    oauth_client_type = oauth_handler.detect_client_type(redirect_uri)

    state = str(uuid.uuid4())
    oauth_states[state] = {
        "redirect_uri": redirect_uri,
        "client_type": "client_app",
        "oauth_client_type": oauth_client_type  # "web" or "ios"
    }

    auth_url = oauth_handler.get_authorization_url(state, code_challenge, redirect_uri, oauth_client_type)
    logger.info(f"Client app login initiated for {redirect_uri} (OAuth client: {oauth_client_type})")
    return {"auth_url": auth_url, "state": state}


@router.get("/google/login")
async def google_login(redirect_uri: str, code_challenge: str):
    """
    DEPRECATED: Use /auth/backstage/google/login or /auth/client/google/login instead

    Initiate Google OAuth login (legacy endpoint with auto-detection)

    Args:
        redirect_uri: Frontend callback URL
        code_challenge: PKCE code challenge (SHA256 of verifier)

    Returns:
        Authorization URL and state parameter
    """
    from api_server import oauth_handler

    # Auto-detect client type from redirect_uri (less secure)
    client_type = "client_app"
    if redirect_uri and ("5173" in redirect_uri or "backstage" in redirect_uri.lower()):
        client_type = "backstage"

    # Auto-detect OAuth client type
    oauth_client_type = oauth_handler.detect_client_type(redirect_uri)

    logger.warning(f"Using deprecated /auth/google/login endpoint. Please use /auth/{client_type}/google/login instead")

    state = str(uuid.uuid4())
    oauth_states[state] = {
        "redirect_uri": redirect_uri,
        "client_type": client_type,
        "oauth_client_type": oauth_client_type
    }

    auth_url = oauth_handler.get_authorization_url(state, code_challenge, redirect_uri, oauth_client_type)
    return {"auth_url": auth_url, "state": state}


async def _handle_oauth_callback(
    code: str,
    state: str,
    code_verifier: str,
    expected_client_type: str = None
):
    """
    Internal helper to handle OAuth callback

    Args:
        code: Authorization code from Google
        state: CSRF protection state parameter
        code_verifier: PKCE code verifier
        expected_client_type: Expected client type (backstage or client_app)

    Returns:
        AuthTokenResponse with access and refresh tokens

    Raises:
        HTTPException: If OAuth fails or user not authorized
    """
    from api_server import oauth_handler, jwt_handler, session_manager, config

    # Validate state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    state_data = oauth_states.pop(state)
    redirect_uri = state_data.get("redirect_uri")
    client_type = state_data.get("client_type", "client_app")
    oauth_client_type = state_data.get("oauth_client_type", "web")  # OAuth client: web/ios

    # Validate client type matches expected (if endpoint-specific)
    if expected_client_type and client_type != expected_client_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid callback: expected {expected_client_type} but got {client_type}"
        )

    # Exchange code for tokens (use correct OAuth client type)
    try:
        google_tokens = await oauth_handler.exchange_code_for_tokens(
            code,
            code_verifier,
            redirect_uri,
            oauth_client_type  # Pass the OAuth client type (web/ios)
        )
        user_info = await oauth_handler.get_user_info(google_tokens["access_token"])
        logger.info(f"Token exchange successful using {oauth_client_type} client")
    except Exception as e:
        logger.error(f"OAuth failed for {oauth_client_type} client: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

    auth_config = config.get("authentication", {})
    user_roles_config = auth_config.get("user_roles", {})

    logger.info(f"Login attempt from {client_type} app for {user_info['email']}")

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


@router.get("/backstage/google/callback", response_model=AuthTokenResponse)
async def backstage_google_callback(code: str, state: str, code_verifier: str):
    """
    Handle Google OAuth callback for BACKSTAGE admin panel

    Args:
        code: Authorization code from Google
        state: CSRF protection state parameter
        code_verifier: PKCE code verifier

    Returns:
        JWT access token and refresh token for backstage user

    Raises:
        HTTPException: If OAuth fails or user not authorized
    """
    return await _handle_oauth_callback(code, state, code_verifier, expected_client_type="backstage")


@router.get("/client/google/callback", response_model=AuthTokenResponse)
async def client_google_callback(code: str, state: str, code_verifier: str):
    """
    Handle Google OAuth callback for CLIENT APP

    Args:
        code: Authorization code from Google
        state: CSRF protection state parameter
        code_verifier: PKCE code verifier

    Returns:
        JWT access token and refresh token for client app user

    Raises:
        HTTPException: If OAuth fails or user not authorized
    """
    return await _handle_oauth_callback(code, state, code_verifier, expected_client_type="client_app")


@router.get("/google/callback", response_model=AuthTokenResponse)
async def google_callback(code: str, state: str, code_verifier: str):
    """
    DEPRECATED: Use /auth/backstage/google/callback or /auth/client/google/callback instead

    Handle Google OAuth callback (legacy endpoint with auto-detection)

    Args:
        code: Authorization code from Google
        state: CSRF protection state parameter
        code_verifier: PKCE code verifier

    Returns:
        JWT access token and refresh token

    Raises:
        HTTPException: If OAuth fails or user not authorized
    """
    logger.warning("Using deprecated /auth/google/callback endpoint")
    return await _handle_oauth_callback(code, state, code_verifier, expected_client_type=None)


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


@router.post("/client/google/verify-token", response_model=AuthTokenResponse)
async def verify_google_id_token(request: IDTokenVerifyRequest):
    """
    Verify Google ID token from native SDK and return app tokens

    This endpoint is for mobile apps using native Google Sign-In SDK.
    The SDK provides an ID token which we verify with Google, then
    return our own access_token and refresh_token.

    Args:
        request: ID token from Google Sign-In SDK

    Returns:
        JWT access token and refresh token for client app user

    Raises:
        HTTPException: If token verification fails or user not allowed
    """
    from api_server import oauth_handler, jwt_handler, session_manager, config

    # Verify ID token with Google (default to iOS client)
    try:
        user_info = await oauth_handler.verify_id_token(request.id_token, client_type="ios")
        logger.info(f"ID token verified for {user_info['email']}")
    except ValueError as e:
        logger.error(f"ID token verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid ID token: {str(e)}")
    except Exception as e:
        logger.error(f"ID token verification error: {e}")
        raise HTTPException(status_code=400, detail=f"Token verification failed: {str(e)}")

    # Ensure email is verified
    if not user_info.get("email_verified"):
        raise HTTPException(status_code=403, detail="Email not verified by Google")

    # Check if public signup is allowed
    auth_config = config.get("authentication", {})
    allow_public = auth_config.get("allow_public_signup", False)

    if not allow_public:
        raise HTTPException(
            status_code=403,
            detail="Client app registration is currently disabled. Please contact administrator."
        )

    # Create user data for client app (always client_user role)
    user_data = {
        "email": user_info["email"],
        "name": user_info["name"],
        "picture": user_info.get("picture"),
        "role": auth_config.get("default_role", "client_user"),
        "scopes": auth_config.get("default_scopes", ["client_app", "read_tours", "user_data"]),
        "client_type": "client_app"
    }

    # Create session and tokens
    refresh_token = session_manager.create_session(user_data)
    access_token = jwt_handler.create_access_token(user_data)

    logger.info(f"User {user_info['email']} logged in via native SDK as client_user")

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Dict, Optional


security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(credentials = Depends(security)) -> Dict:
    """
    Get current user from JWT token

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        User information dictionary

    Raises:
        HTTPException: If token is missing or invalid
    """
    from api_server import jwt_handler

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth token"
        )

    is_valid, payload = jwt_handler.validate_token(credentials.credentials)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=payload.get("error")
        )

    return {
        "email": payload["sub"],
        "name": payload["name"],
        "picture": payload.get("picture"),
        "role": payload.get("role", "client_user"),
        "scopes": payload.get("scopes", []),
        "client_type": payload.get("client_type", "backstage")
    }


async def get_optional_user(credentials = Depends(optional_security)) -> Optional[Dict]:
    """
    Get current user from JWT token if present, otherwise return None.

    This dependency is for endpoints where auth is optional - the endpoint
    can provide different functionality based on whether user is authenticated.

    Args:
        credentials: HTTP Bearer credentials from request (optional)

    Returns:
        User information dictionary if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        from api_server import jwt_handler

        if not jwt_handler:
            return None

        is_valid, payload = jwt_handler.validate_token(credentials.credentials)
        if not is_valid:
            return None

        return {
            "email": payload["sub"],
            "name": payload["name"],
            "picture": payload.get("picture"),
            "role": payload.get("role", "client_user"),
            "scopes": payload.get("scopes", []),
            "client_type": payload.get("client_type", "backstage")
        }
    except Exception:
        return None


def require_role(required_role: str):
    """
    Dependency to require specific role

    Args:
        required_role: Role name required (e.g., "backstage_admin")

    Returns:
        Dependency function that validates role
    """
    async def role_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role} required"
            )
        return current_user
    return role_checker


def require_scope(required_scope: str):
    """
    Dependency to require specific scope

    Args:
        required_scope: Scope name required (e.g., "backstage", "write_tours")

    Returns:
        Dependency function that validates scope
    """
    async def scope_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        if required_scope not in current_user.get("scopes", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope {required_scope} required"
            )
        return current_user
    return scope_checker


def require_backstage_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Require backstage admin role

    Args:
        current_user: Current user from token

    Returns:
        User information if authorized

    Raises:
        HTTPException: If user lacks admin role or backstage scope
    """
    if current_user["role"] != "backstage_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    if "backstage" not in current_user.get("scopes", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backstage access required"
        )
    return current_user


def require_backstage_write(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Require backstage write permission (admin or editor)

    Args:
        current_user: Current user from token

    Returns:
        User information if authorized

    Raises:
        HTTPException: If user lacks write permissions
    """
    allowed_roles = ["backstage_admin", "backstage_editor"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required"
        )
    if "write_tours" not in current_user.get("scopes", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write scope required"
        )
    return current_user


def require_client_app(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Require client app access

    Args:
        current_user: Current user from token

    Returns:
        User information if authorized

    Raises:
        HTTPException: If user lacks client app scope
    """
    if "client_app" not in current_user.get("scopes", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client app access required"
        )
    return current_user

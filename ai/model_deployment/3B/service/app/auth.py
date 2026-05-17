import secrets

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings


def require_service_api_key(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    configured_keys = settings.api_key_list
    if not configured_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_key_not_configured", "message": "Service API key is not configured."},
        )

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing Bearer token."},
        )

    if not any(secrets.compare_digest(token, key) for key in configured_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid API key."},
        )

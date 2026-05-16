from __future__ import annotations

import hmac

from .config import ServiceSettings


BEARER_PREFIX = "Bearer "


def is_authorized(authorization_header: str | None, settings: ServiceSettings) -> bool:
    if not settings.api_key:
        return False
    if not authorization_header or not authorization_header.startswith(BEARER_PREFIX):
        return False

    supplied_key = authorization_header[len(BEARER_PREFIX) :].strip()
    if not supplied_key:
        return False

    return hmac.compare_digest(supplied_key, settings.api_key)

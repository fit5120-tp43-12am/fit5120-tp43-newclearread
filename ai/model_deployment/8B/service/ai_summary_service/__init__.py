"""Standalone ClearRead AI Summary service package."""

from .config import ServiceSettings


def create_app(*args, **kwargs):
    from .main import create_app as _create_app

    return _create_app(*args, **kwargs)

__all__ = ["ServiceSettings", "create_app"]

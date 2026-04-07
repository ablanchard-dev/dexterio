"""Messages d'erreur HTTP sans fuite d'informations internes."""

from __future__ import annotations

from typing import Optional

from config.settings import settings


def safe_http_500_detail(exception: Optional[Exception] = None) -> str:
    if getattr(settings, "EXPOSE_INTERNAL_ERRORS", False) and exception is not None:
        return str(exception)
    return "Internal server error"

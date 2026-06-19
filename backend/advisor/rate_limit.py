from __future__ import annotations

from django.conf import settings
from django.core.cache import cache


def advisor_rate_limit_exceeded(request) -> bool:
    limit = int(getattr(settings, "ADVISOR_RATE_LIMIT_REQUESTS", 60))
    window_seconds = int(getattr(settings, "ADVISOR_RATE_LIMIT_WINDOW_SECONDS", 60))
    if limit <= 0:
        return False

    key = f"advisor-rate:{_client_ip(request)}"
    added = cache.add(key, 1, timeout=window_seconds)
    if added:
        return False

    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return count > limit


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")

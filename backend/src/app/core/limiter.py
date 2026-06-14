"""Rate limiter instance shared across all route modules."""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.environ.get("IC_RATE_LIMIT_ENABLED", "1") != "0",
)

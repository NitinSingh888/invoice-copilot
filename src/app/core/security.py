from __future__ import annotations


def current_role(x_role: str | None) -> str:
    return "priya" if (x_role or "").lower() == "priya" else "maya"

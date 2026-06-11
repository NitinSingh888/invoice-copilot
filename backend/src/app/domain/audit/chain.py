from __future__ import annotations
import hashlib
import json
from collections.abc import Sequence
from typing import Any

GENESIS = "0" * 64

def hash_event(prev_hash: str, event: dict[str, Any]) -> str:
    payload = prev_hash + json.dumps(event, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def chain(events: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    prev = GENESIS
    out: list[dict[str, Any]] = []
    for e in events:
        body = {k: v for k, v in e.items() if k not in ("prev_hash", "hash")}
        h = hash_event(prev, body)
        out.append({**body, "prev_hash": prev, "hash": h})
        prev = h
    return out

def verify_chain(chained: Sequence[dict[str, Any]]) -> bool:
    prev = GENESIS
    for e in chained:
        body = {k: v for k, v in e.items() if k not in ("prev_hash", "hash")}
        if e.get("prev_hash") != prev or e.get("hash") != hash_event(prev, body):
            return False
        prev = e["hash"]
    return True

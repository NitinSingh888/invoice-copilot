from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.db.models.vendor import Vendor


def _normalize(name: str) -> str:
    """Lower-case, strip, and collapse internal whitespace."""
    return re.sub(r"\s+", " ", name.strip().lower())


def add(s: Session, vendor: Vendor) -> Vendor:
    s.add(vendor)
    s.flush()
    return vendor


def get(s: Session, vendor_id: str, *, org_id: str | None = None) -> Vendor | None:
    v = s.get(Vendor, vendor_id)
    if v is None:
        return None
    if org_id is not None and v.org_id != org_id:
        return None
    return v


def resolve(s: Session, name: str, *, org_id: str | None = None) -> Vendor | None:
    """Alias-aware vendor lookup.

    Priority:
    1. Exact match on canonical_name.
    2. Case/whitespace-normalised match on canonical_name.
    3. Raw ``name`` or its normalised form appears in a vendor's ``aliases``.
    """
    q = s.query(Vendor)
    if org_id is not None:
        q = q.filter(Vendor.org_id == org_id)

    # 1. Exact canonical_name match
    exact = q.filter(Vendor.canonical_name == name).first()
    if exact is not None:
        return exact

    # 2. Normalised canonical_name match
    norm = _normalize(name)
    for vendor in q.all():
        if _normalize(vendor.canonical_name) == norm:
            return vendor

    # 3. aliases match (raw or normalised)
    for vendor in q.all():
        aliases: list[str] = vendor.aliases or []
        if name in aliases:
            return vendor
        if any(_normalize(a) == norm for a in aliases):
            return vendor

    return None


def resolve_from_text(s: Session, text: str, *, org_id: str | None = None) -> Vendor | None:
    """Find the vendor whose canonical_name (or alias) best matches *text*.

    Matching strategy (in priority order):
    1. The full canonical_name appears verbatim as a substring of *text*
       (case-insensitive, e.g. "Cyberdyne Systems" in "review Cyberdyne Systems invoice").
    2. Any individual significant word (≥4 chars) from the canonical_name appears
       in *text* (e.g. "cyberdyne" from "Cyberdyne Systems" in "review cyberdyne invoice").

    When multiple vendors match at the same priority level, prefer the one with
    the longest canonical_name (most specific).
    """
    norm_text = _normalize(text)
    best: Vendor | None = None
    best_len = 0
    best_priority = 999  # lower = better

    q = s.query(Vendor)
    if org_id is not None:
        q = q.filter(Vendor.org_id == org_id)

    for vendor in q.all():
        cname_norm = _normalize(vendor.canonical_name)
        priority: int | None = None
        match_len = 0

        # Priority 1: full canonical name is a substring
        if cname_norm in norm_text:
            priority = 1
            match_len = len(cname_norm)
        else:
            # Priority 2: any significant word from canonical name appears in text
            words = [w for w in cname_norm.split() if len(w) >= 4]
            if any(w in norm_text for w in words):
                priority = 2
                match_len = len(cname_norm)

        # Check aliases at same priority levels
        for alias in vendor.aliases or []:
            alias_norm = _normalize(alias)
            if alias_norm in norm_text:
                p = 1
                ml = len(alias_norm)
            else:
                alias_words = [w for w in alias_norm.split() if len(w) >= 4]
                if any(w in norm_text for w in alias_words):
                    p = 2
                    ml = len(alias_norm)
                else:
                    continue
            if priority is None or p < priority or (p == priority and ml > match_len):
                priority = p
                match_len = ml

        if priority is not None:
            if priority < best_priority or (priority == best_priority and match_len > best_len):
                best = vendor
                best_len = match_len
                best_priority = priority

    return best


def status_of(s: Session, name: str, *, org_id: str | None = None) -> str:
    vendor = resolve(s, name, org_id=org_id)
    if vendor is None:
        return "new"
    return vendor.status

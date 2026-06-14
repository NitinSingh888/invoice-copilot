from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.clients.llm.base import LLMClient
from app.clients.llm.types import ChatMessage, CommandSpec
from app.core.config import get_settings
from app.db.models.invoice import Invoice
from app.domain.policy.findings import Finding
from app.repositories import invoice_repo, vendor_repo
from app.schemas.chat import ChatMessageIn
from app.services import (
    enrichment_service,
    pipeline_service,
    policy_service,
)

_LIST_CAP = 25  # max rows for a "review / list" result

_DEFAULT_SMALLTALK = (
    "I'm your Invoice Copilot — I read each invoice, match it to its PO, auto-clear "
    'the safe ones, and ask you about the rest. Try "process today\'s invoices", '
    '"review the Acme invoice", or "how many need review?".'
)


def _scope_base(db: Session, message: str, *, org_id: str | None) -> list[Invoice]:
    """Default a query to TODAY's working queue (what the user is looking at); broaden
    to all invoices (incl. multi-day history) only when the message asks for it."""
    if re.search(
        r"\b(all|every|everything|entire|history|historic|past|previous|prior|ever|so far)\b",
        message,
        re.IGNORECASE,
    ):
        return invoice_repo.list_all(db, org_id=org_id)
    return invoice_repo.list_today(db, org_id=org_id)


def _smalltalk_reply(
    client: LLMClient, db: Session, msgs: list[ChatMessage], org_id: str | None
) -> str:
    """A real, contextual answer for general questions — not a canned line."""
    from collections import Counter

    today = invoice_repo.list_today(db, org_id=org_id)
    counts = Counter(i.status for i in today)
    context = {
        "assistant": "Invoice Copilot, an AI accounts-payable assistant",
        "today_queue": {
            "total": len(today),
            "received_unprocessed": counts.get("received", 0),
            "needs_review": counts.get("needs", 0),
            "queued_for_payment": counts.get("queued", 0),
            "blocked": counts.get("blocked", 0),
        },
        "guidance": (
            "Answer the user's actual question briefly and helpfully. If they ask why the "
            "queue shows 0 queued/cleared, explain that nothing in today's batch has been "
            "processed yet (all 'received'), and that broad totals include past days shown "
            "in History; suggest they say 'process today's invoices'."
        ),
    }
    try:
        reply = client.converse(history=msgs, context=context)
        text = (reply.text or "").strip()
        return text or _DEFAULT_SMALLTALK
    except Exception:
        return _DEFAULT_SMALLTALK


def handle(
    client: LLMClient,
    db: Session,
    *,
    message: str,
    history: list[ChatMessageIn],
    org_id: str | None = None,
) -> tuple[str, str, dict[str, Any] | None]:
    """Handle a user message via the conversation agent.

    The LLM proposes a structured command; deterministic service calls execute it.
    The LLM never directly authorises money — all execution goes through existing
    services which enforce the guard.

    Returns (reply_text, intent, result_dict_or_None).
    """
    msgs: list[ChatMessage] = [
        ChatMessage(role=h.role, content=h.content) for h in history
    ]
    msgs.append(ChatMessage(role="user", content=message))

    cmd: CommandSpec = client.parse_command(message=message, history=msgs[:-1])

    # ------------------------------------------------------------------ #
    # Smalltalk — nothing to execute                                       #
    # ------------------------------------------------------------------ #
    if cmd.action == "smalltalk":
        return (_smalltalk_reply(client, db, msgs, org_id), "smalltalk", None)

    # ------------------------------------------------------------------ #
    # PROCESS                                                              #
    # Base = today's received invoices; filters narrow the set.           #
    # ------------------------------------------------------------------ #
    if cmd.action == "process":
        today = invoice_repo.list_today(db, org_id=org_id)
        base = [inv for inv in today if inv.status == "received"]
        candidates = _filter_invoices(db, cmd, base=base, org_id=org_id)
        label = _filter_label(cmd) or "today"
        queued = needs = blocked = 0
        for inv in candidates:
            invoice_data = invoice_repo.to_domain(inv)
            confidence = inv.confidence or "HIGH"
            proc = pipeline_service.process_invoice(db, invoice_data, confidence, org_id=org_id)
            verdict = proc.decision.verdict.value
            if verdict == "AUTO_CLEAR":
                queued += 1
            elif verdict == "ESCALATE":
                needs += 1
            else:  # BLOCK
                blocked += 1
        result: dict[str, Any] = {
            "queued": queued,
            "needs": needs,
            "blocked": blocked,
            "label": label,
        }
        total = queued + needs + blocked
        if total == 0:
            # Nothing new to process — show existing counts instead
            from collections import Counter

            counts = Counter(inv.status for inv in today)
            existing_needs = counts.get("needs", 0)
            existing_blocked = counts.get("blocked", 0)
            existing_queued = counts.get("queued", 0)
            # Update result dict so the frontend card shows real numbers
            result["queued"] = existing_queued
            result["needs"] = existing_needs
            result["blocked"] = existing_blocked
            existing_total = existing_needs + existing_blocked + existing_queued
            if existing_total > 0:
                parts: list[str] = []
                if existing_needs:
                    parts.append(f"{existing_needs} awaiting your review")
                if existing_blocked:
                    parts.append(f"{existing_blocked} blocked")
                if existing_queued:
                    parts.append(f"{existing_queued} already queued for payment")
                text = (
                    f"No new invoices to process — {', '.join(parts)}."
                )
            else:
                text = "No invoices to process today."
        else:
            text = (
                f"Processed {total} invoice(s) [{label}]: "
                f"{queued} queued, {needs} need review, {blocked} blocked."
            )
        return (text, "process_batch", result)

    # ------------------------------------------------------------------ #
    # REVIEW                                                               #
    # If invoice_ref is set → single invoice review.                      #
    # If no filters → try _resolve_target for a named entity.            #
    # Otherwise → list matching invoices (capped at _LIST_CAP).           #
    # ------------------------------------------------------------------ #
    if cmd.action == "review":
        _has_filters = bool(cmd.vendor or cmd.amount_op or cmd.status)

        # Explicit invoice_ref from parser
        if cmd.invoice_ref:
            inv_ref: Invoice | None = _resolve_by_ref(db, cmd.invoice_ref, org_id=org_id)
            if inv_ref is None:
                inv_ref = _resolve_target(db, message, org_id=org_id)
            if inv_ref is not None:
                review_result = _build_review_result(db, inv_ref, org_id=org_id)
                label_text = inv_ref.invoice_number or inv_ref.id
                text = f"Here's {label_text} from {inv_ref.vendor}:"
                return (text, "review_invoice", review_result)
            return (
                f"I couldn't find invoice \"{cmd.invoice_ref}\". "
                "Try an invoice number like INV-4495 or a vendor name.",
                "review_invoice",
                {"not_found": True, "query": cmd.invoice_ref},
            )

        # No filters at all — check if the message names a specific entity
        if not _has_filters:
            inv_ent: Invoice | None = _resolve_target(db, message, org_id=org_id)
            if inv_ent is not None:
                review_result = _build_review_result(db, inv_ent, org_id=org_id)
                label_text = inv_ent.invoice_number or inv_ent.id
                text = f"Here's {label_text} from {inv_ent.vendor}:"
                return (text, "review_invoice", review_result)
            # No entity found and no filters → return not_found
            return (
                "I couldn't find a specific invoice in that message. "
                "Try 'review invoices from <vendor>' or 'review invoice <number>'.",
                "review_invoice",
                {"not_found": True, "query": message.strip()[:60]},
            )

        # Has filters → list mode
        base_all = _scope_base(db, message, org_id=org_id)
        candidates = _filter_invoices(db, cmd, base=base_all, org_id=org_id)
        # A single match — or an "explain/why" question — shows the full review
        # card, whose summary explains the reason (e.g. "explain why SAECO was
        # blocked"). For "why" with several matches, pick the one whose state the
        # user is asking about (blocked → needs → held → routed).
        wants_explain = bool(re.search(r"\b(why|explain|reason)\b", message, re.IGNORECASE))
        if candidates and (len(candidates) == 1 or wants_explain):
            target = candidates[0]
            if wants_explain:
                for st in ("blocked", "needs", "held", "routed"):
                    match = [c for c in candidates if c.status == st]
                    if match:
                        target = match[0]
                        break
            review_result = _build_review_result(db, target, org_id=org_id)
            inv0 = review_result["invoice"]
            text = f"Here's {inv0.get('invoice_number') or inv0.get('id')} from {inv0.get('vendor')}:"
            return (text, "review_invoice", review_result)
        label = _filter_label(cmd) or "all"
        full_count = len(candidates)
        page = candidates[:_LIST_CAP]
        rows = [
            {
                "id": inv.id,
                "vendor": inv.vendor,
                "amount": str(inv.amount) if inv.amount is not None else None,
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "po_number": inv.po_number,
            }
            for inv in page
        ]
        result = {"list": rows, "label": label, "count": full_count}
        text = f"Found {full_count} invoice(s) [{label}]."
        if full_count > _LIST_CAP:
            text += f" Showing first {_LIST_CAP}."
        return (text, "list", result)

    # ------------------------------------------------------------------ #
    # COUNT / SUM                                                          #
    # ------------------------------------------------------------------ #
    if cmd.action in ("count", "sum"):
        base_all = _scope_base(db, message, org_id=org_id)
        candidates = _filter_invoices(db, cmd, base=base_all, org_id=org_id)
        # When no specific status filter, exclude resolved invoices from totals
        # so "total amount pending" doesn't include already-approved ones
        if not cmd.status:
            _terminal = {"cleared", "queued", "rejected"}
            candidates = [inv for inv in candidates if inv.status not in _terminal]
        label = _filter_label(cmd) or "pending"
        if cmd.action == "count":
            value_str = str(len(candidates))
            text = f"There are {len(candidates)} invoice(s) matching [{label}]."
        else:
            total_amount = sum(
                (inv.amount or Decimal("0")) for inv in candidates
            )
            value_str = f"${total_amount:,.2f}"
            text = f"Total amount for [{label}]: {value_str}."
        result = {"aggregate": {"label": label, "value": value_str}}
        return (text, "aggregate", result)

    # ------------------------------------------------------------------ #
    # APPROVE / HOLD / ROUTE — bulk confirm (no execution)                #
    # ------------------------------------------------------------------ #
    if cmd.action in ("approve", "hold", "route"):
        # Bulk actions only target ACTIONABLE invoices (awaiting a decision) —
        # never re-touch already-cleared history — unless the user names a status.
        if cmd.status:
            base = invoice_repo.list_by_status(db, cmd.status, org_id=org_id)
        else:
            base = invoice_repo.list_by_status(db, "received", org_id=org_id) + invoice_repo.list_by_status(
                db, "needs", org_id=org_id
            )
        candidates = _filter_invoices(db, cmd, base=base, org_id=org_id)
        label = _filter_label(cmd) or "matching"
        ids = [inv.id for inv in candidates]
        total_amount = sum(
            (inv.amount or Decimal("0")) for inv in candidates
        )
        total_str = f"${total_amount:,.2f}"
        bulk: dict[str, Any] = {
            "action": cmd.action,
            "ids": ids,
            "count": len(ids),
            "total": total_str,
            "label": label,
        }
        if cmd.route_to:
            bulk["route_to"] = cmd.route_to
        result = {"bulk": bulk}
        dest = f" to {cmd.route_to}" if cmd.route_to else ""
        text = (
            f"This will {cmd.action} {len(ids)} invoice(s){dest} totaling "
            f"{total_str} [{label}]. Confirm?"
        )
        return (text, "bulk_confirm", result)

    # ------------------------------------------------------------------ #
    # Legacy single-invoice intents delegated from old converse flow      #
    # (kept for backward-compat with tests that still use them)           #
    # ------------------------------------------------------------------ #
    return (_smalltalk_reply(client, db, msgs, org_id), "smalltalk", None)


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------


def _filter_invoices(
    db: Session,
    cmd: CommandSpec,
    *,
    base: list[Invoice],
    org_id: str | None = None,
) -> list[Invoice]:
    """Return the subset of *base* that satisfies all filters in *cmd*."""
    result: list[Invoice] = list(base)

    # invoice_ref → single match (handled by caller; skip list filter)
    # We do NOT filter by invoice_ref here because review uses it separately.

    # vendor filter — fuzzy via vendor_repo or case-insensitive substring
    if cmd.vendor:
        vendor_name: str | None = None
        resolved = vendor_repo.resolve_from_text(db, cmd.vendor, org_id=org_id)
        if resolved is not None:
            vendor_name = resolved.canonical_name
        result = [
            inv
            for inv in result
            if (
                (vendor_name is not None and inv.vendor == vendor_name)
                or (
                    inv.vendor is not None
                    and cmd.vendor.lower() in inv.vendor.lower()
                )
            )
        ]

    # amount filter
    if cmd.amount_op and cmd.amount_value is not None:
        op = cmd.amount_op
        val = cmd.amount_value
        filtered: list[Invoice] = []
        for inv in result:
            amt = inv.amount
            if amt is None:
                continue
            if op == "<" and amt < val:
                filtered.append(inv)
            elif op == "<=" and amt <= val:
                filtered.append(inv)
            elif op == ">" and amt > val:
                filtered.append(inv)
            elif op == ">=" and amt >= val:
                filtered.append(inv)
            elif op == "==" and amt == val:
                filtered.append(inv)
        result = filtered

    # status filter
    if cmd.status:
        result = [inv for inv in result if inv.status == cmd.status]

    return result


_STATUS_LABELS = {
    "received": "waiting to be processed",
    "needs": "need review",
    "queued": "queued for payment",
    "blocked": "blocked",
    "held": "on hold",
    "routed": "routed",
}


def _filter_label(cmd: CommandSpec) -> str:
    """Build a human-readable description of the active filters."""
    parts: list[str] = []
    if cmd.vendor:
        parts.append(f"vendor={cmd.vendor}")
    if cmd.amount_op and cmd.amount_value is not None:
        parts.append(f"amount{cmd.amount_op}{cmd.amount_value}")
    if cmd.status:
        parts.append(_STATUS_LABELS.get(cmd.status, f"status={cmd.status}"))
    return ", ".join(parts)


def _resolve_by_ref(db: Session, ref: str, *, org_id: str | None = None) -> Invoice | None:
    """Resolve an invoice by id or invoice_number token."""
    for cand in (ref, ref.lower(), ref.upper()):
        inv = invoice_repo.get(db, cand, org_id=org_id)
        if inv is not None:
            return inv
    return invoice_repo.get_by_invoice_number(db, ref, org_id=org_id)


# ---------------------------------------------------------------------------
# Internal helpers for review_invoice (single)
# ---------------------------------------------------------------------------


def _resolve_target(db: Session, message: str, *, org_id: str | None = None) -> Invoice | None:
    """Resolve the invoice a message refers to — by id, invoice_number, or vendor."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9/_.-]{3,}", message)
    for tok in tokens:
        for cand in (tok, tok.lower(), tok.upper()):
            inv = invoice_repo.get(db, cand, org_id=org_id)
            if inv is not None:
                return inv
        inv = invoice_repo.get_by_invoice_number(db, tok, org_id=org_id)
        if inv is not None:
            return inv
    vendor = vendor_repo.resolve_from_text(db, message, org_id=org_id)
    if vendor is not None:
        q = db.query(Invoice).filter(Invoice.vendor == vendor.canonical_name)
        if org_id is not None:
            q = q.filter(Invoice.org_id == org_id)
        candidates = q.order_by(Invoice.created_at.desc()).all()
        priority = [c for c in candidates if c.status in ("needs", "blocked")]
        return priority[0] if priority else (candidates[0] if candidates else None)
    return None


def _has_review_entity(db: Session, message: str, *, org_id: str | None = None) -> bool:
    """True if the message references a resolvable invoice."""
    return _resolve_target(db, message, org_id=org_id) is not None


def _build_review_result(
    db: Session, inv: Invoice, *, org_id: str | None = None
) -> dict[str, Any]:
    """Build the structured review result for a single invoice."""
    settings = get_settings()
    inv_data = invoice_repo.to_domain(inv)
    enr = enrichment_service.enrich(db, inv_data, org_id=org_id)
    findings = policy_service.run(inv_data, enr, settings.tolerance_pct)
    salient = [f for f in findings if f.code != "PO_MATCH_OK"]
    return {
        "invoice": {
            "id": inv.id,
            "vendor": inv.vendor,
            "amount": str(inv.amount) if inv.amount is not None else None,
            "invoice_number": inv.invoice_number,
            "po_number": inv.po_number,
            "status": inv.status,
            "verdict": inv.verdict,
            "confidence": inv.confidence,
        },
        "findings": [
            {"code": f.code, "severity": f.severity.value, "detail": f.detail}
            for f in salient
        ],
        "summary": _build_summary(inv, salient),
    }


def _build_summary(inv: Invoice, findings: list[Finding]) -> str:
    codes = [f.code for f in findings]
    parts: list[str] = []
    if "DUPLICATE_EXACT" in codes:
        parts.append("blocked as exact duplicate of a previously cleared invoice")
    if "UNKNOWN_VENDOR" in codes:
        parts.append("vendor not yet approved")
    if "MISSING_PO" in codes:
        parts.append("no PO referenced")
    if "OVER_TOLERANCE" in codes:
        parts.append("amount exceeds PO tolerance")
    if "DUPLICATE_SUSPECT" in codes:
        parts.append("suspected duplicate (same vendor + amount seen recently)")
    if not parts:
        if inv.status == "needs":
            parts.append("escalated for manual review")
        elif inv.status == "blocked":
            parts.append("blocked by policy")
        else:
            parts.append(f"status is {inv.status}")
    vendor_name = inv.vendor or "unknown vendor"
    inv_num = inv.invoice_number or inv.id
    return f"{inv_num} from {vendor_name} is {inv.status}: {'; '.join(parts)}."

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.clients.llm.base import LLMClient
from app.clients.llm.types import AgentReply, ChatMessage
from app.core.config import get_settings
from app.db.models.invoice import Invoice
from app.domain.policy.findings import Finding
from app.repositories import invoice_repo, vendor_repo
from app.schemas.chat import ChatMessageIn
from app.services import (
    audit_service,
    enrichment_service,
    execution_service,
    learning_service,
    pipeline_service,
    policy_service,
)


def handle(
    client: LLMClient,
    db: Session,
    *,
    message: str,
    history: list[ChatMessageIn],
    role: str,
) -> tuple[str, str, dict[str, Any] | None]:
    """Handle a user message via the conversation agent.

    The LLM proposes an intent; deterministic service calls execute it.
    The LLM never directly authorises money — all execution goes through
    existing services which enforce the guard.

    Returns (reply_text, intent, result_dict_or_None).
    """
    msgs: list[ChatMessage] = [
        ChatMessage(role=h.role, content=h.content) for h in history
    ]
    msgs.append(ChatMessage(role="user", content=message))

    reply: AgentReply = client.converse(history=msgs, context={})

    result: dict[str, Any] | None = None
    intent = reply.intent

    # Deterministic override: a "review / show / look at / pull up / what about
    # <entity>" message should resolve and return structured invoice data even if
    # the LLM labelled it "explain" or "smalltalk" (the real model often maps
    # "review" -> "explain"). Messages explicitly asking for the trail/audit/history
    # keep their "explain" intent.
    if intent in ("explain", "show_trail", "smalltalk", "review_invoice"):
        wants_trail = bool(re.search(r"\b(trail|audit|history|log)\b", message, re.I))
        wants_review = bool(
            re.search(
                r"\b(review|show|see|look|pull up|detail|about|check|info|status of)\b",
                message,
                re.I,
            )
        )
        if not wants_trail and (wants_review or intent == "review_invoice"):
            if _has_review_entity(db, message):
                intent = "review_invoice"

    if intent == "process_batch":
        invoices = invoice_repo.list_by_status(db, "received")
        queued = needs = blocked = 0
        for inv in invoices:
            invoice_data = invoice_repo.to_domain(inv)
            confidence = inv.confidence or "HIGH"
            proc = pipeline_service.process_invoice(db, invoice_data, confidence)
            verdict = proc.decision.verdict.value
            if verdict == "AUTO_CLEAR":
                queued += 1
            elif verdict == "ESCALATE":
                needs += 1
            else:  # BLOCK
                blocked += 1
        result = {"queued": queued, "needs": needs, "blocked": blocked}

    elif intent in ("explain", "show_trail"):
        inv_id = reply.args.get("invoice_id")
        if inv_id:
            events = audit_service.trail(db, str(inv_id))
            trail_list = [
                {
                    "seq": e.seq,
                    "module": e.module,
                    "action": e.action,
                    "actor": e.actor,
                    "rationale": e.rationale,
                }
                for e in events
            ]
            result = {"invoice_id": inv_id, "trail": trail_list}

    elif intent in ("approve", "route", "hold"):
        inv_id = reply.args.get("invoice_id")
        if inv_id:
            execution_service.execute(db, str(inv_id), intent, actor=role)
            result = {"invoice_id": inv_id, "action": intent}

    elif intent == "propose_rule":
        proposal = learning_service.propose_rule(db)
        if proposal is not None:
            result = {
                "proposal": {
                    "vendor": proposal.candidate.vendor,
                    "threshold_pct": str(proposal.threshold_pct),
                    "route": proposal.route,
                }
            }
        else:
            result = None

    elif intent == "review_invoice":
        result = _resolve_review_invoice(db, message)

    elif intent == "smalltalk":
        result = None

    # For a resolved review, replace the LLM narration (which may ask for details
    # the code already has) with a clean confirmation that matches the card shown.
    if intent == "review_invoice" and result is not None:
        if result.get("not_found"):
            text = (
                f"I couldn't find an invoice matching “{result.get('query')}”. "
                "Try an invoice number like INV-4495 or a vendor name."
            )
        else:
            inv = result["invoice"]
            label = inv.get("invoice_number") or inv.get("id")
            text = f"Here's {label} from {inv.get('vendor')}:"
        return (text, intent, result)

    return (reply.text, intent, result)


# ---------------------------------------------------------------------------
# Internal helpers for review_invoice
# ---------------------------------------------------------------------------


def _has_review_entity(db: Session, message: str) -> bool:
    """True if the message references a resolvable invoice (INV-#### or a vendor)."""
    if re.search(r"INV-\d+", message, re.IGNORECASE):
        return True
    return vendor_repo.resolve_from_text(db, message) is not None


def _resolve_review_invoice(db: Session, message: str) -> dict[str, Any]:
    """Deterministically resolve and return a structured invoice review."""
    settings = get_settings()

    # 1. Try to extract an explicit INV-#### from the message.
    inv_id_match = re.search(r"(INV-\d+)", message, re.IGNORECASE)
    inv: Invoice | None = None
    query_entity: str = message.strip()

    if inv_id_match:
        inv_id = inv_id_match.group(1).upper()
        query_entity = inv_id
        inv = invoice_repo.get(db, inv_id)
    else:
        # 2. Try to find a vendor name substring in the message.
        vendor = vendor_repo.resolve_from_text(db, message)
        if vendor is not None:
            query_entity = vendor.canonical_name
            # Prefer invoice in needs/blocked status, else most recent.
            candidates = (
                db.query(Invoice)
                .filter(Invoice.vendor == vendor.canonical_name)
                .order_by(Invoice.created_at.desc())
                .all()
            )
            priority = [c for c in candidates if c.status in ("needs", "blocked")]
            inv = priority[0] if priority else (candidates[0] if candidates else None)

    if inv is None:
        return {"not_found": True, "query": query_entity}

    # 3. Recompute findings via policy service (uses enrichment).
    inv_data = invoice_repo.to_domain(inv)
    enr = enrichment_service.enrich(db, inv_data)
    findings = policy_service.run(inv_data, enr, settings.tolerance_pct)

    # Salient findings: exclude trivial INFO PO_MATCH_OK
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

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .types import AgentReply, ChatMessage, Confidence, ExtractedField, ExtractedInvoice

# Confidence ordering for comparison
_CONF_RANK: dict[str, int] = {"HIGH": 2, "MED": 1, "LOW": 0}


def _lower_conf(a: Confidence, b: Confidence) -> Confidence:
    """Return the lower of two confidence levels."""
    return a if _CONF_RANK[a] <= _CONF_RANK[b] else b


class MockClient:
    name = "mock"

    # ------------------------------------------------------------------
    # extract_invoice
    # ------------------------------------------------------------------
    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        """Parse key: value lines from text.  Fully deterministic."""
        raw: dict[str, str] = {}
        for line in text.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                raw[key.strip().lower()] = value.strip()

        # --- vendor ---
        vendor_raw = raw.get("vendor")
        vendor_conf: Confidence = "HIGH" if vendor_raw else "LOW"
        vendor_field = ExtractedField(value=vendor_raw or None, confidence=vendor_conf)

        # --- amount ---
        amount_raw = raw.get("amount")
        amount_value: Decimal | None = None
        amount_conf: Confidence = "LOW"
        if amount_raw:
            cleaned = amount_raw.replace("$", "").replace(",", "").strip()
            try:
                amount_value = Decimal(cleaned)
                amount_conf = "HIGH"
            except InvalidOperation:
                amount_conf = "LOW"
        amount_field = ExtractedField(
            value=str(amount_value) if amount_value is not None else None,
            confidence=amount_conf,
        )

        # --- po_number ---
        po_raw = raw.get("po") or raw.get("po_number")
        po_conf: Confidence = "HIGH" if po_raw else "LOW"
        po_field = ExtractedField(value=po_raw or None, confidence=po_conf)

        # --- invoice_number ---
        inv_raw = raw.get("invoice_number") or raw.get("invoice")
        inv_conf: Confidence = "HIGH" if inv_raw else "LOW"
        inv_field = ExtractedField(value=inv_raw or None, confidence=inv_conf)

        # overall_confidence = lowest band among the 4 decision fields
        overall: Confidence = "HIGH"
        for conf in (vendor_conf, amount_conf, po_conf, inv_conf):
            overall = _lower_conf(overall, conf)

        fields: dict[str, ExtractedField] = {
            "vendor": vendor_field,
            "amount": amount_field,
            "po_number": po_field,
            "invoice_number": inv_field,
        }

        return ExtractedInvoice(
            vendor=vendor_raw or None,
            amount=amount_value,
            po_number=po_raw or None,
            invoice_number=inv_raw or None,
            fields=fields,
            overall_confidence=overall,
        )

    # ------------------------------------------------------------------
    # converse
    # ------------------------------------------------------------------
    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply:
        last = history[-1].content.lower() if history else ""

        # Extract optional invoice id from message
        inv_id_match = re.search(r"(INV-\d+)", history[-1].content if history else "")
        args: dict[str, Any] = {}
        if inv_id_match:
            args["invoice_id"] = inv_id_match.group(1)

        if re.search(r"process|today|run the batch|go ahead", last):
            intent = "process_batch"
            text = "Starting the batch processing run now."
        elif re.search(
            r"\b(review|show|look at|find|pull up|pull-up)\b",
            last,
        ) and re.search(
            r"(inv-\d+|invoice|vendor|cyberdyne|acme|northwind|stark|globex|initech|hooli|soylent|meridian|wayne|umbrella)",
            last,
        ):
            intent = "review_invoice"
            text = "Here is the structured review for that invoice."
        elif re.search(r"why|trail|escalat|injection|4495|pay now", last):
            intent = "explain"
            text = "Here is the explanation for that invoice decision."
        elif re.search(r"\bapprove\b", last):
            intent = "approve"
            text = "Invoice has been approved."
        elif re.search(r"\broute\b", last):
            intent = "route"
            text = "Routing the invoice as requested."
        elif re.search(r"\bhold\b", last):
            intent = "hold"
            text = "Invoice placed on hold."
        elif re.search(r"rule|learn", last):
            intent = "propose_rule"
            text = "Proposing a new routing rule based on observed patterns."
        else:
            intent = "smalltalk"
            text = "I'm your Invoice Copilot. How can I help?"
            args = {}

        return AgentReply(text=text, intent=intent, args=args)

    # ------------------------------------------------------------------
    # explain_rule
    # ------------------------------------------------------------------
    def explain_rule(
        self,
        *,
        vendor: str,
        over_pcts: list[Decimal],
        threshold_pct: Decimal,
        route: str,
    ) -> str:
        pcts_str = ", ".join(f"{p:.0%}" for p in over_pcts)
        return (
            f"Inferred from corrections at {pcts_str} over PO → "
            f"generalizes to ~{threshold_pct:.0%}; routes {vendor} to {route}."
        )

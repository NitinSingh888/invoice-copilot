from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .types import AgentReply, ChatMessage, CommandSpec, Confidence, ExtractedField, ExtractedInvoice
from .usage import record_usage

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
        record_usage("mock", "mock", 0, 0)
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
        record_usage("mock", "mock", 0, 0)
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
    # parse_command — deterministic regex / keyword heuristics
    # ------------------------------------------------------------------
    def parse_command(
        self, *, message: str, history: list[ChatMessage]
    ) -> CommandSpec:
        """Parse a natural-language message into a CommandSpec using regex heuristics."""
        record_usage("mock", "mock", 0, 0)
        low = message.lower().strip()

        # ---- action detection (order matters: more-specific first) ----
        if re.search(r"\b(how many|count)\b", low):
            action = "count"
        elif re.search(r"\b(sum|total amount|total value)\b", low):
            action = "sum"
        elif re.search(r"\b(approve)\b", low):
            action = "approve"
        elif re.search(r"\b(hold)\b", low):
            action = "hold"
        elif re.search(r"\b(route)\b", low):
            action = "route"
        elif re.search(r"\b(process|run the batch|go ahead|run batch)\b", low):
            action = "process"
        elif re.search(r"\b(review|show|list|see|find|pull up|pull-up)\b", low):
            action = "review"
        else:
            return CommandSpec(action="smalltalk")

        # ---- amount filter ----
        amount_op: str | None = None
        amount_value: Decimal | None = None
        amount_pat = re.search(
            r"\b(under|below|less than|over|above|greater than|exactly|at least|at most|=|<=|>=|<|>)\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            low,
        )
        if amount_pat:
            word = amount_pat.group(1).strip()
            raw_val = amount_pat.group(2).replace(",", "")
            try:
                amount_value = Decimal(raw_val)
                if word in ("under", "below", "less than", "<"):
                    amount_op = "<"
                elif word in ("<=", "at most"):
                    amount_op = "<="
                elif word in ("over", "above", "greater than", ">"):
                    amount_op = ">"
                elif word in (">=", "at least"):
                    amount_op = ">="
                elif word in ("exactly", "="):
                    amount_op = "=="
            except InvalidOperation:
                pass

        # ---- status filter ----
        status: str | None = None
        if re.search(r"\b(need review|needs review|needs|escalated)\b", low):
            status = "needs"
        elif re.search(r"\bblocked\b", low):
            status = "blocked"
        elif re.search(r"\bqueued\b", low):
            status = "queued"
        elif re.search(r"\bheld\b", low):
            status = "held"
        elif re.search(r"\brouted\b", low):
            status = "routed"
        elif (
            re.search(r"\b(received|pending|unprocessed)\b", low)
            or "to be processed" in low
            or "to process" in low
            or "waiting to" in low
        ):
            status = "received"

        # ---- invoice_ref (specific invoice id / number) ----
        invoice_ref: str | None = None
        ref_match = re.search(
            r"\b(INV[-/][A-Za-z0-9/_.-]+|[A-Za-z]{2,}[-/][0-9]+[A-Za-z0-9/_.-]*|[0-9]{5,})\b",
            message,
        )
        if ref_match:
            invoice_ref = ref_match.group(1)

        # ---- vendor ----
        vendor: str | None = None
        vendor_match = re.search(
            r"\b(?:from|of|vendor|for)\s+([A-Za-z][A-Za-z0-9 .&,'-]{2,30?)(?:\s+invoice|\s+invoices|$)",
            message,
            re.I,
        )
        if vendor_match:
            vendor = vendor_match.group(1).strip()
        else:
            # Try "invoices from <Vendor>" pattern
            vendor_match2 = re.search(
                r"invoices?\s+from\s+([A-Za-z][A-Za-z0-9 .&,'-]{2,30})",
                message,
                re.I,
            )
            if vendor_match2:
                vendor = vendor_match2.group(1).strip()

        # ---- route_to ----
        route_to: str | None = None
        route_match = re.search(r"\bto\s+([A-Za-z][a-z]+)\b", message, re.I)
        if action == "route" and route_match:
            route_to = route_match.group(1)

        return CommandSpec(
            action=action,
            vendor=vendor,
            amount_op=amount_op,
            amount_value=amount_value,
            status=status,
            invoice_ref=invoice_ref,
            route_to=route_to,
        )

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
        record_usage("mock", "mock", 0, 0)
        pcts_str = ", ".join(f"{p:.0%}" for p in over_pcts)
        return (
            f"Inferred from corrections at {pcts_str} over PO → "
            f"generalizes to ~{threshold_pct:.0%}; routes {vendor} to {route}."
        )

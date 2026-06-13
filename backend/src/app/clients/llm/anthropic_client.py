from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .types import AgentReply, ChatMessage, CommandSpec, Confidence, ExtractedField, ExtractedInvoice
from .usage import record_usage

# System prompts
_EXTRACT_SYSTEM = (
    "You are an invoice data extraction assistant. "
    "Extract invoice fields from the provided text or image and return ONLY a JSON object "
    "with exactly these keys: vendor (string or null), amount (string decimal or null), "
    "po_number (string or null), invoice_number (string or null), "
    "confidence (one of: HIGH, MED, LOW). "
    "No explanation, no markdown, only the raw JSON object."
)

_CONVERSE_SYSTEM = (
    "You are Invoice Copilot, an accounts-payable AI assistant. "
    "Respond with ONLY a JSON object with keys: "
    "text (string reply to show user), "
    "intent (one of: process_batch, explain, show_trail, approve, route, hold, propose_rule, smalltalk), "
    "args (object with optional invoice_id and other parameters). "
    "No explanation, no markdown, only the raw JSON object."
)

_FALLBACK_INVOICE = ExtractedInvoice(
    vendor=None,
    amount=None,
    po_number=None,
    invoice_number=None,
    fields={
        "vendor": ExtractedField(value=None, confidence="LOW"),
        "amount": ExtractedField(value=None, confidence="LOW"),
        "po_number": ExtractedField(value=None, confidence="LOW"),
        "invoice_number": ExtractedField(value=None, confidence="LOW"),
    },
    overall_confidence="LOW",
)

_FALLBACK_REPLY = AgentReply(
    text="I'm sorry, I couldn't process that request right now.",
    intent="smalltalk",
    args={},
)

_FALLBACK_COMMAND = CommandSpec(action="smalltalk")

_COMMAND_SYSTEM = """\
You are an invoice command parser. Extract a structured command from the user's message.
Return ONLY a JSON object with these exact keys (all optional except "action"):
  action       – one of: process | review | approve | hold | route | count | sum | smalltalk
  vendor       – vendor name if mentioned (string or null)
  amount_op    – one of: "<", "<=", ">", ">=", "==" (if an amount comparison is present, else null)
  amount_value – numeric string if comparison present (e.g. "100", "1000.50"), else null
  status       – one of: received | needs | queued | blocked | routed | held (if mentioned, else null)
  invoice_ref  – specific invoice number or id if ONE invoice is named (else null)
  route_to     – person/team name if action=route (else null)

Rules:
- "process" = run the processing pipeline on matching invoices
- "review" = show details / list matching invoices
- "approve" = approve matching invoices (return bulk confirm — do NOT execute)
- "hold" = place matching invoices on hold (return bulk confirm — do NOT execute)
- "route" = route matching invoices (return bulk confirm — do NOT execute)
- "count" = count matching invoices
- "sum" = sum the amount of matching invoices
- "smalltalk" = anything that doesn't map to invoice operations

Examples (JSON output shown after →):
  "process all invoices from Reyes" → {"action":"process","vendor":"Reyes"}
  "review invoices under $100" → {"action":"review","amount_op":"<","amount_value":"100"}
  "approve all under $50" → {"action":"approve","amount_op":"<","amount_value":"50"}
  "how many need review?" → {"action":"count","status":"needs"}
  "process those over 1000" → {"action":"process","amount_op":">","amount_value":"1000"}
  "review invoice 72128555" → {"action":"review","invoice_ref":"72128555"}
  "process today's invoices" → {"action":"process"}
  "show all invoices from Palmer" → {"action":"review","vendor":"Palmer"}
  "route blocked invoices to Priya" → {"action":"route","status":"blocked","route_to":"Priya"}
  "how many are blocked?" → {"action":"count","status":"blocked"}
  "sum of all needs invoices" → {"action":"sum","status":"needs"}
  "hi" → {"action":"smalltalk"}
  "what can you do?" → {"action":"smalltalk"}

No explanation, no markdown, only the raw JSON object.\
"""


def _parse_json_from_text(text: str) -> dict[str, Any]:
    """Extract a JSON object from text that may contain markdown fences."""
    # Try direct parse first
    stripped = text.strip()
    try:
        return dict(json.loads(stripped))
    except json.JSONDecodeError:
        pass
    # Try extracting from code fence
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", stripped)
    if match:
        try:
            return dict(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    # Try finding first { ... } block
    match2 = re.search(r"\{[\s\S]+\}", stripped)
    if match2:
        try:
            return dict(json.loads(match2.group(0)))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


def _conf_from_str(val: object) -> Confidence:
    if isinstance(val, str) and val.upper() in ("HIGH", "MED", "LOW"):
        return val.upper()
    return "LOW"


class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None  # lazily initialised

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _record(self, response: Any) -> None:
        """Report this response's actual token usage to the metering sink."""
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                record_usage(
                    self.name,
                    self._model,
                    int(getattr(usage, "input_tokens", 0) or 0),
                    int(getattr(usage, "output_tokens", 0) or 0),
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # extract_invoice
    # ------------------------------------------------------------------
    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        try:
            client = self._get_client()
            if image_b64:
                # Detect media type from the base64 magic prefix — Anthropic rejects
                # a mismatch (e.g. JPEG bytes declared as image/png).
                if image_b64.startswith("/9j/"):
                    media_type = "image/jpeg"
                elif image_b64.startswith("R0lGOD"):
                    media_type = "image/gif"
                elif image_b64.startswith("UklGR"):
                    media_type = "image/webp"
                else:
                    media_type = "image/png"
                content: list[dict[str, Any]] = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": "Extract the invoice fields from this image."},
                ]
            else:
                content = [{"type": "text", "text": text}]

            response = client.messages.create(
                model=self._model,
                max_tokens=512,
                system=_EXTRACT_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
            self._record(response)
            raw_text: str = response.content[0].text
            data = _parse_json_from_text(raw_text)
        except Exception:
            return _FALLBACK_INVOICE

        try:
            vendor = data.get("vendor") or None
            vendor_conf: Confidence = "HIGH" if vendor else "LOW"

            amount_str = data.get("amount")
            amount_value: Decimal | None = None
            amount_conf: Confidence = "LOW"
            if amount_str:
                try:
                    amount_value = Decimal(str(amount_str).replace(",", "").replace("$", ""))
                    amount_conf = "HIGH"
                except InvalidOperation:
                    amount_conf = "LOW"

            po = data.get("po_number") or None
            po_conf: Confidence = "HIGH" if po else "LOW"

            inv = data.get("invoice_number") or None
            inv_conf: Confidence = "HIGH" if inv else "LOW"

            # Overall confidence from response, but cap at lowest field
            resp_conf = _conf_from_str(data.get("confidence", "LOW"))
            # Use min of reported and computed
            _rank = {"HIGH": 2, "MED": 1, "LOW": 0}
            field_confs = [vendor_conf, amount_conf, po_conf, inv_conf]
            computed_min = min(field_confs, key=lambda c: _rank[c])
            overall: Confidence = (
                computed_min if _rank[computed_min] < _rank[resp_conf] else resp_conf
            )

            fields: dict[str, ExtractedField] = {
                "vendor": ExtractedField(value=vendor, confidence=vendor_conf),
                "amount": ExtractedField(
                    value=str(amount_value) if amount_value is not None else None,
                    confidence=amount_conf,
                ),
                "po_number": ExtractedField(value=po, confidence=po_conf),
                "invoice_number": ExtractedField(value=inv, confidence=inv_conf),
            }

            return ExtractedInvoice(
                vendor=vendor,
                amount=amount_value,
                po_number=po,
                invoice_number=inv,
                fields=fields,
                overall_confidence=overall,
            )
        except Exception:
            return _FALLBACK_INVOICE

    # ------------------------------------------------------------------
    # converse
    # ------------------------------------------------------------------
    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply:
        try:
            client = self._get_client()
            messages = [{"role": m.role, "content": m.content} for m in history]
            if context:
                messages = [
                    {
                        "role": "user",
                        "content": f"Context: {json.dumps(context)}\n\nProceed with the conversation.",
                    },
                    *messages,
                ]

            response = client.messages.create(
                model=self._model,
                max_tokens=512,
                system=_CONVERSE_SYSTEM,
                messages=messages,
            )
            self._record(response)
            raw_text = response.content[0].text
            data = _parse_json_from_text(raw_text)
        except Exception:
            return _FALLBACK_REPLY

        try:
            text_val = str(data.get("text", ""))
            intent_val = str(data.get("intent", "smalltalk"))
            args_val = data.get("args", {})
            if not isinstance(args_val, dict):
                args_val = {}
            return AgentReply(text=text_val, intent=intent_val, args=dict(args_val))
        except Exception:
            return _FALLBACK_REPLY

    # ------------------------------------------------------------------
    # parse_command
    # ------------------------------------------------------------------
    def parse_command(
        self, *, message: str, history: list[ChatMessage]
    ) -> CommandSpec:
        try:
            client = self._get_client()
            messages = [{"role": m.role, "content": m.content} for m in history]
            messages.append({"role": "user", "content": message})
            response = client.messages.create(
                model=self._model,
                max_tokens=256,
                system=_COMMAND_SYSTEM,
                messages=messages,
            )
            self._record(response)
            raw_text: str = response.content[0].text
            data = _parse_json_from_text(raw_text)
        except Exception:
            return _FALLBACK_COMMAND

        try:
            from decimal import Decimal as _D, InvalidOperation

            action = str(data.get("action", "smalltalk"))
            valid_actions = {
                "process", "review", "approve", "hold", "route", "count", "sum", "smalltalk"
            }
            if action not in valid_actions:
                action = "smalltalk"

            vendor = data.get("vendor") or None
            if vendor is not None:
                vendor = str(vendor)

            amount_op = data.get("amount_op") or None
            valid_ops = {"<", "<=", ">", ">=", "=="}
            if amount_op not in valid_ops:
                amount_op = None

            amount_value: Decimal | None = None
            raw_av = data.get("amount_value")
            if raw_av is not None:
                try:
                    amount_value = _D(str(raw_av).replace(",", "").replace("$", ""))
                except InvalidOperation:
                    amount_value = None

            status = data.get("status") or None
            valid_statuses = {"received", "needs", "queued", "blocked", "routed", "held"}
            if status not in valid_statuses:
                status = None

            invoice_ref = data.get("invoice_ref") or None
            if invoice_ref is not None:
                invoice_ref = str(invoice_ref)

            route_to = data.get("route_to") or None
            if route_to is not None:
                route_to = str(route_to)

            return CommandSpec(
                action=action,
                vendor=vendor,
                amount_op=amount_op,
                amount_value=amount_value,
                status=status,
                invoice_ref=invoice_ref,
                route_to=route_to,
            )
        except Exception:
            return _FALLBACK_COMMAND

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
        try:
            client = self._get_client()
            pcts_str = ", ".join(f"{p:.1%}" for p in over_pcts)
            prompt = (
                f"Vendor '{vendor}' has been corrected at {pcts_str} over PO amount. "
                f"Infer a routing rule with threshold ~{threshold_pct:.1%} to route to '{route}'. "
                "Explain in one concise sentence."
            )
            response = client.messages.create(
                model=self._model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            self._record(response)
            return str(response.content[0].text).strip()
        except Exception:
            pcts_str2 = ", ".join(f"{p:.0%}" for p in over_pcts)
            return (
                f"Inferred from corrections at {pcts_str2} over PO → "
                f"generalizes to ~{threshold_pct:.0%}; routes {vendor} to {route}."
            )

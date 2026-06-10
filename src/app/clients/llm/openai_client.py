from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .types import AgentReply, ChatMessage, Confidence, ExtractedField, ExtractedInvoice

_EXTRACT_SYSTEM = (
    "You are an invoice data extraction assistant. "
    "Extract invoice fields from the provided text and return ONLY a JSON object "
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


def _parse_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        return dict(json.loads(stripped))
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", stripped)
    if match:
        try:
            return dict(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
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


class OpenAIClient:
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None  # lazily initialised

    def _get_client(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    # ------------------------------------------------------------------
    # extract_invoice
    # ------------------------------------------------------------------
    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        try:
            client = self._get_client()
            user_content: str | list[dict[str, Any]]
            if image_b64:
                user_content = [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                    {"type": "text", "text": "Extract the invoice fields from this image."},
                ]
            else:
                user_content = text

            response = client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _EXTRACT_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=512,
            )
            raw_text: str = response.choices[0].message.content or ""
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

            resp_conf = _conf_from_str(data.get("confidence", "LOW"))
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
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": _CONVERSE_SYSTEM}
            ]
            if context:
                messages.append(
                    {
                        "role": "user",
                        "content": f"Context: {json.dumps(context)}\n\nProceed with the conversation.",
                    }
                )
            messages.extend({"role": m.role, "content": m.content} for m in history)

            response = client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=messages,
                max_tokens=512,
            )
            raw_text = response.choices[0].message.content or ""
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
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            return str(response.choices[0].message.content or "").strip()
        except Exception:
            pcts_str2 = ", ".join(f"{p:.0%}" for p in over_pcts)
            return (
                f"Inferred from corrections at {pcts_str2} over PO → "
                f"generalizes to ~{threshold_pct:.0%}; routes {vendor} to {route}."
            )

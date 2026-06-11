from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.clients.llm.base import LLMClient
from app.clients.llm.types import AgentReply, ChatMessage
from app.repositories import invoice_repo
from app.schemas.chat import ChatMessageIn
from app.services import audit_service, execution_service, learning_service, pipeline_service


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

    elif intent == "smalltalk":
        result = None

    return (reply.text, intent, result)

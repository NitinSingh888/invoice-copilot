from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents import conversation_agent
from app.api.deps import get_db, get_llm, get_role
from app.clients.llm.base import LLMClient
from app.schemas.chat import ChatIn, ChatOut

router = APIRouter()


@router.post("", response_model=ChatOut)
def chat(
    body: ChatIn,
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
    llm: LLMClient = Depends(get_llm),
) -> ChatOut:
    text, intent, result = conversation_agent.handle(
        llm,
        db,
        message=body.message,
        history=body.history,
        role=role,
    )
    return ChatOut(reply=text, intent=intent, result=result)

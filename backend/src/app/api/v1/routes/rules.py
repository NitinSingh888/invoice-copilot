from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.agents import induction_agent
from app.api.deps import get_current_org, get_db, get_llm
from app.clients.llm.base import LLMClient
from app.core.exceptions import AppError, NotFoundError
from app.repositories import rule_repo
from app.schemas.rule import ActivateRuleIn, CreateRuleIn, PatternOut, RuleOut, RuleProposalOut, RuleStatusIn
from app.services import learning_service

router = APIRouter()


@router.get("", response_model=list[RuleOut])
def list_rules(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> list[RuleOut]:
    return [RuleOut.model_validate(r) for r in rule_repo.list_all(db, org_id=org_id)]


@router.post("", status_code=201, response_model=RuleOut)
def create_rule(
    body: CreateRuleIn,
    db: Session = Depends(get_db),
    x_role: str = Header(default="user"),
    org_id: str = Depends(get_current_org),
) -> RuleOut:
    rule = learning_service.create_rule(
        db,
        vendor=body.vendor,
        finding_code=body.finding_code,
        max_over_pct=body.max_over_pct,
        min_amount=body.min_amount,
        route=body.route,
        created_by=x_role,
        org_id=org_id,
    )
    return RuleOut.model_validate(rule)


@router.post("/propose", response_model=None)
def propose_rule(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> Response | RuleProposalOut:
    p = learning_service.propose_rule(db, org_id=org_id)
    if p is None:
        return Response(status_code=204)
    return RuleProposalOut(
        candidate=PatternOut(
            vendor=p.candidate.vendor,
            finding_code=p.candidate.finding_code,
            action=p.candidate.action,
            example_ids=list(p.candidate.example_ids),
            over_pcts=list(p.candidate.over_pcts),
        ),
        threshold_pct=p.threshold_pct,
        route=p.route,
    )


@router.post("/activate", status_code=201, response_model=RuleOut)
def activate_rule(
    body: ActivateRuleIn,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    org_id: str = Depends(get_current_org),
) -> RuleOut:
    p = learning_service.propose_rule(db, org_id=org_id)
    if p is None:
        raise AppError("no rule to activate")
    note = induction_agent.reasoning(
        llm,
        vendor=p.candidate.vendor or "",
        over_pcts=list(p.candidate.over_pcts),
        threshold_pct=body.threshold_pct,
        route=body.route,
    )
    rule = learning_service.activate_rule(
        db,
        proposal=p,
        threshold_pct=body.threshold_pct,
        route=body.route,
        reasoning=note,
        org_id=org_id,
    )
    return RuleOut.model_validate(rule)


@router.patch("/{rule_id}", response_model=RuleOut)
def set_rule_status(
    rule_id: str,
    body: RuleStatusIn,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> RuleOut:
    try:
        rule = learning_service.set_rule_status(db, rule_id, body.status, org_id=org_id)
    except ValueError as exc:
        raise NotFoundError(str(exc)) from exc
    return RuleOut.model_validate(rule)

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    DecisionMemo,
    DocumentEvidence,
    ResearchAssumption,
    ResearchChallenge,
    ResearchClaim,
    ResearchSubject,
    User,
)
from app.schemas import (
    DecisionMemoCreate,
    DecisionMemoResponse,
    ResearchAssumptionCreate,
    ResearchAssumptionResponse,
    ResearchChallengeCreate,
    ResearchChallengeResponse,
    ResearchClaimCreate,
    ResearchClaimResponse,
    ResearchSubjectCreate,
    ResearchSubjectResponse,
    ResearchSubjectWorkspaceResponse,
)

router = APIRouter(prefix="/api/research-subjects", tags=["research-subjects"])


async def _get_subject_for_user(
    subject_id: str,
    user: User,
    db: AsyncSession,
) -> ResearchSubject:
    subject = await db.get(ResearchSubject, subject_id)
    if not subject or subject.user_id != user.id:
        raise HTTPException(status_code=404, detail="研究对象不存在")
    return subject


@router.post("", response_model=ResearchSubjectResponse)
async def create_research_subject(
    data: ResearchSubjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    subject = ResearchSubject(
        user_id=user.id,
        organization_id=user.organization_id,
        company_name=data.company_name,
        ticker=data.ticker,
        industry=data.industry,
        current_view=data.current_view,
        confidence_level=data.confidence_level,
        evidence_strength=data.evidence_strength,
        last_view_updated_at=now if data.current_view else None,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return ResearchSubjectResponse.model_validate(subject)


@router.get("", response_model=list[ResearchSubjectResponse])
async def list_research_subjects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchSubject)
        .where(ResearchSubject.user_id == user.id)
        .order_by(desc(ResearchSubject.updated_at))
    )
    return [ResearchSubjectResponse.model_validate(item) for item in result.scalars().all()]


@router.get("/{subject_id}/workspace", response_model=ResearchSubjectWorkspaceResponse)
async def get_research_subject_workspace(
    subject_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)

    claims_result = await db.execute(
        select(ResearchClaim)
        .where(ResearchClaim.research_subject_id == subject.id)
        .where(ResearchClaim.user_id == user.id)
        .order_by(desc(ResearchClaim.updated_at))
    )
    assumptions_result = await db.execute(
        select(ResearchAssumption)
        .where(ResearchAssumption.research_subject_id == subject.id)
        .where(ResearchAssumption.user_id == user.id)
        .order_by(desc(ResearchAssumption.updated_at))
    )
    challenges_result = await db.execute(
        select(ResearchChallenge)
        .where(ResearchChallenge.research_subject_id == subject.id)
        .where(ResearchChallenge.user_id == user.id)
        .order_by(desc(ResearchChallenge.created_at))
    )
    memos_result = await db.execute(
        select(DecisionMemo)
        .where(DecisionMemo.research_subject_id == subject.id)
        .where(DecisionMemo.user_id == user.id)
        .order_by(desc(DecisionMemo.created_at))
    )
    evidence_count_result = await db.execute(
        select(func.count(DocumentEvidence.id))
        .where(DocumentEvidence.research_subject_id == subject.id)
        .where(DocumentEvidence.user_id == user.id)
    )

    return ResearchSubjectWorkspaceResponse(
        subject=ResearchSubjectResponse.model_validate(subject),
        claims=[ResearchClaimResponse.model_validate(item) for item in claims_result.scalars().all()],
        assumptions=[
            ResearchAssumptionResponse.model_validate(item)
            for item in assumptions_result.scalars().all()
        ],
        challenges=[
            ResearchChallengeResponse.model_validate(item)
            for item in challenges_result.scalars().all()
        ],
        decision_memos=[
            DecisionMemoResponse.model_validate(item)
            for item in memos_result.scalars().all()
        ],
        evidence_count=evidence_count_result.scalar_one(),
    )


@router.get("/{subject_id}", response_model=ResearchSubjectResponse)
async def get_research_subject(
    subject_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    return ResearchSubjectResponse.model_validate(subject)


@router.post("/{subject_id}/claims", response_model=ResearchClaimResponse)
async def create_research_claim(
    subject_id: str,
    data: ResearchClaimCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    claim = ResearchClaim(
        research_subject_id=subject.id,
        user_id=user.id,
        content=data.content,
        direction=data.direction,
        confidence_level=data.confidence_level,
        evidence_strength=data.evidence_strength,
        status=data.status,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return ResearchClaimResponse.model_validate(claim)


@router.post("/{subject_id}/assumptions", response_model=ResearchAssumptionResponse)
async def create_research_assumption(
    subject_id: str,
    data: ResearchAssumptionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    assumption = ResearchAssumption(
        research_subject_id=subject.id,
        user_id=user.id,
        content=data.content,
        category=data.category,
        confidence_level=data.confidence_level,
        status=data.status,
    )
    db.add(assumption)
    await db.commit()
    await db.refresh(assumption)
    return ResearchAssumptionResponse.model_validate(assumption)


@router.post("/{subject_id}/challenges", response_model=ResearchChallengeResponse)
async def create_research_challenge(
    subject_id: str,
    data: ResearchChallengeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    if data.claim_id:
        claim = await db.get(ResearchClaim, data.claim_id)
        if not claim or claim.user_id != user.id or claim.research_subject_id != subject.id:
            raise HTTPException(status_code=404, detail="被挑战的判断不存在")

    challenge = ResearchChallenge(
        research_subject_id=subject.id,
        user_id=user.id,
        claim_id=data.claim_id,
        question=data.question,
        risk_level=data.risk_level,
        suggested_action=data.suggested_action,
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return ResearchChallengeResponse.model_validate(challenge)


@router.post("/{subject_id}/decision-memos", response_model=DecisionMemoResponse)
async def create_decision_memo(
    subject_id: str,
    data: DecisionMemoCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    memo = DecisionMemo(
        research_subject_id=subject.id,
        user_id=user.id,
        current_conclusion=data.current_conclusion,
        key_basis=data.key_basis,
        biggest_uncertainty=data.biggest_uncertainty,
        suggested_action=data.suggested_action,
        review_status=data.review_status,
    )
    db.add(memo)
    await db.commit()
    await db.refresh(memo)
    return DecisionMemoResponse.model_validate(memo)

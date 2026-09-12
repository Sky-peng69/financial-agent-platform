import json
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
    EvidenceSnippetResponse,
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
from app.services.research_asset_generator import generate_research_assets

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


def _parse_evidence_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]


def _evidence_items_for_asset(
    raw: str | None,
    evidence_by_id: dict[str, DocumentEvidence],
) -> tuple[list[str], list[EvidenceSnippetResponse]]:
    evidence_ids = _parse_evidence_ids(raw)
    evidence_items = [
        EvidenceSnippetResponse.model_validate(evidence_by_id[evidence_id])
        for evidence_id in evidence_ids
        if evidence_id in evidence_by_id
    ]
    return evidence_ids, evidence_items


def _claim_response(
    claim: ResearchClaim,
    evidence_by_id: dict[str, DocumentEvidence],
) -> ResearchClaimResponse:
    evidence_ids, evidence_items = _evidence_items_for_asset(claim.evidence_ids, evidence_by_id)
    return ResearchClaimResponse(
        id=claim.id,
        research_subject_id=claim.research_subject_id,
        content=claim.content,
        direction=claim.direction,
        confidence_level=claim.confidence_level,
        evidence_strength=claim.evidence_strength,
        status=claim.status,
        evidence_ids=evidence_ids,
        verification_status=claim.verification_status or "needs_review",
        evidence_items=evidence_items,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )


def _assumption_response(
    assumption: ResearchAssumption,
    evidence_by_id: dict[str, DocumentEvidence],
) -> ResearchAssumptionResponse:
    evidence_ids, evidence_items = _evidence_items_for_asset(
        assumption.evidence_ids,
        evidence_by_id,
    )
    return ResearchAssumptionResponse(
        id=assumption.id,
        research_subject_id=assumption.research_subject_id,
        content=assumption.content,
        category=assumption.category,
        confidence_level=assumption.confidence_level,
        status=assumption.status,
        evidence_ids=evidence_ids,
        verification_status=assumption.verification_status or "needs_review",
        evidence_items=evidence_items,
        created_at=assumption.created_at,
        updated_at=assumption.updated_at,
    )


def _asset_evidence_ids(
    indexes: list[int],
    evidence_items: list[DocumentEvidence],
) -> list[str]:
    evidence_ids: list[str] = []
    for index in indexes:
        if 1 <= index <= len(evidence_items):
            evidence_id = evidence_items[index - 1].id
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids


def _asset_verification(
    indexes: list[int],
    evidence_items: list[DocumentEvidence],
    model_status: str,
) -> tuple[list[str], str]:
    evidence_ids = _asset_evidence_ids(indexes, evidence_items)
    if evidence_ids:
        return evidence_ids, model_status
    if evidence_items:
        return [evidence_items[0].id], "needs_review"
    return [], "insufficient"


async def _build_workspace_response(
    subject: ResearchSubject,
    user: User,
    db: AsyncSession,
) -> ResearchSubjectWorkspaceResponse:
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
    evidence_result = await db.execute(
        select(DocumentEvidence)
        .where(DocumentEvidence.research_subject_id == subject.id)
        .where(DocumentEvidence.user_id == user.id)
    )
    evidence_by_id = {item.id: item for item in evidence_result.scalars().all()}

    return ResearchSubjectWorkspaceResponse(
        subject=ResearchSubjectResponse.model_validate(subject),
        claims=[
            _claim_response(item, evidence_by_id)
            for item in claims_result.scalars().all()
        ],
        assumptions=[
            _assumption_response(item, evidence_by_id)
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
    return await _build_workspace_response(subject, user, db)


@router.get("/{subject_id}", response_model=ResearchSubjectResponse)
async def get_research_subject(
    subject_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    return ResearchSubjectResponse.model_validate(subject)


@router.post("/{subject_id}/generate-assets", response_model=ResearchSubjectWorkspaceResponse)
async def generate_subject_assets(
    subject_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    evidence_result = await db.execute(
        select(DocumentEvidence)
        .where(DocumentEvidence.research_subject_id == subject.id)
        .where(DocumentEvidence.user_id == user.id)
        .order_by(DocumentEvidence.created_at, DocumentEvidence.chunk_index)
        .limit(20)
    )
    evidence_items = evidence_result.scalars().all()
    if not any(item.text.strip() for item in evidence_items):
        raise HTTPException(status_code=400, detail="请先上传可解析的研究材料")

    try:
        assets = await generate_research_assets(subject, evidence_items)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="AI 服务暂不可用，请检查模型配置后重试") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="生成结果未达到结构化要求，请重试") from exc

    for item in assets["claims"]:
        evidence_ids, verification_status = _asset_verification(
            item["evidence_indexes"],
            evidence_items,
            item["verification_status"],
        )
        db.add(ResearchClaim(
            research_subject_id=subject.id,
            user_id=user.id,
            content=item["content"],
            direction=item["direction"],
            confidence_level=item["confidence_level"],
            evidence_strength=item["evidence_strength"],
            status=item["status"],
            evidence_ids=json.dumps(evidence_ids, ensure_ascii=False) if evidence_ids else None,
            verification_status=verification_status,
        ))

    for item in assets["assumptions"]:
        evidence_ids, verification_status = _asset_verification(
            item["evidence_indexes"],
            evidence_items,
            item["verification_status"],
        )
        db.add(ResearchAssumption(
            research_subject_id=subject.id,
            user_id=user.id,
            content=item["content"],
            category=item["category"],
            confidence_level=item["confidence_level"],
            status=item["status"],
            evidence_ids=json.dumps(evidence_ids, ensure_ascii=False) if evidence_ids else None,
            verification_status=verification_status,
        ))

    for item in assets["challenges"]:
        db.add(ResearchChallenge(
            research_subject_id=subject.id,
            user_id=user.id,
            question=item["question"],
            risk_level=item["risk_level"],
            suggested_action=item["suggested_action"],
        ))

    memo_data = assets["decision_memo"]
    db.add(DecisionMemo(
        research_subject_id=subject.id,
        user_id=user.id,
        current_conclusion=memo_data["current_conclusion"],
        key_basis=memo_data["key_basis"],
        biggest_uncertainty=memo_data["biggest_uncertainty"],
        suggested_action=memo_data["suggested_action"],
        review_status=memo_data["review_status"],
    ))

    first_claim = assets["claims"][0]
    subject.current_view = memo_data["current_conclusion"]
    subject.confidence_level = first_claim["confidence_level"]
    subject.evidence_strength = first_claim["evidence_strength"]
    subject.last_view_updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(subject)
    return await _build_workspace_response(subject, user, db)


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

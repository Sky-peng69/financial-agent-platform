import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    DecisionMemo,
    DocumentEvidence,
    ResearchAssumption,
    ResearchAssetAudit,
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
    ResearchAssetAuditResponse,
    ResearchAssetReviewUpdate,
    ResearchChallengeCreate,
    ResearchChallengeResponse,
    ResearchReportResponse,
    ResearchStartRequest,
    ResearchClaimCreate,
    ResearchClaimResponse,
    ResearchSubjectCreate,
    ResearchSubjectResponse,
    ResearchSubjectWorkspaceResponse,
)
from app.models import ResearchReport
from app.services.orchestrator import run_orchestrated_analysis_sse
from app.services.report_builder import (
    REPORT_STYLES,
    build_report_prompt,
    create_report_record,
    normalize_formats,
    normalize_report_style,
    report_response,
)
from app.services.research_asset_generator import generate_research_assets

router = APIRouter(prefix="/api/research-subjects", tags=["research-subjects"])

REVIEW_STATUSES = {"needs_review", "active", "confirmed", "rejected"}


async def _get_subject_for_user(
    subject_id: str,
    user: User,
    db: AsyncSession,
) -> ResearchSubject:
    subject = await db.get(ResearchSubject, subject_id)
    if not subject or subject.user_id != user.id:
        raise HTTPException(status_code=404, detail="研究对象不存在")
    return subject


async def _get_claim_for_subject(
    claim_id: str,
    subject: ResearchSubject,
    user: User,
    db: AsyncSession,
) -> ResearchClaim:
    claim = await db.get(ResearchClaim, claim_id)
    if not claim or claim.user_id != user.id or claim.research_subject_id != subject.id:
        raise HTTPException(status_code=404, detail="判断不存在")
    return claim


async def _get_assumption_for_subject(
    assumption_id: str,
    subject: ResearchSubject,
    user: User,
    db: AsyncSession,
) -> ResearchAssumption:
    assumption = await db.get(ResearchAssumption, assumption_id)
    if not assumption or assumption.user_id != user.id or assumption.research_subject_id != subject.id:
        raise HTTPException(status_code=404, detail="假设不存在")
    return assumption


def _apply_review_update(
    item: ResearchClaim | ResearchAssumption,
    data: ResearchAssetReviewUpdate,
) -> str:
    action = "updated"
    if data.content is not None:
        content = data.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="内容不能为空")
        item.content = content
        action = "edited"

    if data.status is not None:
        if data.status not in REVIEW_STATUSES:
            raise HTTPException(status_code=400, detail="复核状态无效")
        note = data.review_note.strip() if data.review_note else None
        if data.status == "rejected" and not note:
            raise HTTPException(status_code=400, detail="驳回时必须填写原因")
        item.status = data.status
        item.review_note = note
        item.reviewed_at = datetime.now(timezone.utc) if data.status in {"confirmed", "rejected"} else None
        if data.status == "confirmed":
            action = "confirmed"
        elif data.status == "rejected":
            action = "rejected"
        else:
            action = "updated"
    elif data.review_note is not None:
        item.review_note = data.review_note.strip() or None
        action = "review_note_updated"
    return action


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
    history_by_asset_id: dict[str, list[ResearchAssetAudit]] | None = None,
) -> ResearchClaimResponse:
    history_by_asset_id = history_by_asset_id or {}
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
        review_note=claim.review_note,
        reviewed_at=claim.reviewed_at,
        history=[
            ResearchAssetAuditResponse.model_validate(item)
            for item in history_by_asset_id.get(claim.id, [])
        ],
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )


def _assumption_response(
    assumption: ResearchAssumption,
    evidence_by_id: dict[str, DocumentEvidence],
    history_by_asset_id: dict[str, list[ResearchAssetAudit]] | None = None,
) -> ResearchAssumptionResponse:
    history_by_asset_id = history_by_asset_id or {}
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
        review_note=assumption.review_note,
        reviewed_at=assumption.reviewed_at,
        history=[
            ResearchAssetAuditResponse.model_validate(item)
            for item in history_by_asset_id.get(assumption.id, [])
        ],
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


async def _evidence_by_id_for_subject(
    subject: ResearchSubject,
    user: User,
    db: AsyncSession,
) -> dict[str, DocumentEvidence]:
    evidence_result = await db.execute(
        select(DocumentEvidence)
        .where(DocumentEvidence.research_subject_id == subject.id)
        .where(DocumentEvidence.user_id == user.id)
    )
    return {item.id: item for item in evidence_result.scalars().all()}


async def _history_by_asset_for_subject(
    subject: ResearchSubject,
    user: User,
    db: AsyncSession,
) -> dict[str, list[ResearchAssetAudit]]:
    history_result = await db.execute(
        select(ResearchAssetAudit)
        .where(ResearchAssetAudit.research_subject_id == subject.id)
        .where(ResearchAssetAudit.user_id == user.id)
        .order_by(desc(ResearchAssetAudit.created_at))
    )
    history_by_asset_id: dict[str, list[ResearchAssetAudit]] = {}
    for item in history_result.scalars().all():
        history_by_asset_id.setdefault(item.asset_id, []).append(item)
    return history_by_asset_id


def _add_asset_audit(
    db: AsyncSession,
    *,
    subject: ResearchSubject,
    user: User,
    asset_type: str,
    asset_id: str,
    action: str,
    previous_content: str | None,
    new_content: str | None,
    previous_status: str | None,
    new_status: str | None,
    review_note: str | None,
) -> None:
    db.add(ResearchAssetAudit(
        research_subject_id=subject.id,
        user_id=user.id,
        asset_type=asset_type,
        asset_id=asset_id,
        action=action,
        previous_content=previous_content,
        new_content=new_content,
        previous_status=previous_status,
        new_status=new_status,
        review_note=review_note,
    ))


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
    evidence_by_id = await _evidence_by_id_for_subject(subject, user, db)
    history_by_asset_id = await _history_by_asset_for_subject(subject, user, db)

    return ResearchSubjectWorkspaceResponse(
        subject=ResearchSubjectResponse.model_validate(subject),
        claims=[
            _claim_response(item, evidence_by_id, history_by_asset_id)
            for item in claims_result.scalars().all()
        ],
        assumptions=[
            _assumption_response(item, evidence_by_id, history_by_asset_id)
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


@router.get("/{subject_id}/reports", response_model=list[ResearchReportResponse])
async def list_subject_reports(
    subject_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    result = await db.execute(
        select(ResearchReport)
        .where(ResearchReport.research_subject_id == subject.id)
        .where(ResearchReport.user_id == user.id)
        .order_by(desc(ResearchReport.created_at))
    )
    return [report_response(item) for item in result.scalars().all()]


@router.post("/{subject_id}/start-research-stream")
async def start_subject_research_stream(
    subject_id: str,
    data: ResearchStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    report_style = normalize_report_style(data.report_style)
    formats = normalize_formats(data.formats)
    style_label = REPORT_STYLES[report_style]["label"]
    title = f"弈金-{subject.company_name}-{style_label}"
    user_input = build_report_prompt(
        title=title,
        user_input=(
            f"请对 A 股上市公司 {subject.company_name}"
            f"{f'（{subject.ticker}）' if subject.ticker else ''} 进行自动联网研究。"
            "请自行检索公开资料，不要求用户上传材料。"
        ),
        report_style=report_style,
    )

    async def event_stream():
        async for event in run_orchestrated_analysis_sse(
            user_input=user_input,
            title=title,
            user_id=user.id,
            db=db,
            file_ids=[],
        ):
            if event.get("type") == "done":
                markdown = event.get("output_data") or ""
                report = create_report_record(
                    user=user,
                    title=title,
                    markdown=markdown,
                    report_style=report_style,
                    formats=formats,
                    task_id=event.get("task_id"),
                    research_subject_id=subject.id,
                )
                db.add(report)
                subject.current_view = markdown[:1200]
                subject.last_view_updated_at = datetime.now(timezone.utc)
                await db.commit()
                event["report"] = report_response(report)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
    return _claim_response(claim, {})


@router.patch("/{subject_id}/claims/{claim_id}", response_model=ResearchClaimResponse)
async def update_research_claim(
    subject_id: str,
    claim_id: str,
    data: ResearchAssetReviewUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    claim = await _get_claim_for_subject(claim_id, subject, user, db)
    previous_content = claim.content
    previous_status = claim.status
    action = _apply_review_update(claim, data)
    _add_asset_audit(
        db,
        subject=subject,
        user=user,
        asset_type="claim",
        asset_id=claim.id,
        action=action,
        previous_content=previous_content,
        new_content=claim.content,
        previous_status=previous_status,
        new_status=claim.status,
        review_note=data.review_note.strip() if data.review_note else None,
    )
    await db.commit()
    await db.refresh(claim)
    evidence_by_id = await _evidence_by_id_for_subject(subject, user, db)
    history_by_asset_id = await _history_by_asset_for_subject(subject, user, db)
    return _claim_response(claim, evidence_by_id, history_by_asset_id)


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
    return _assumption_response(assumption, {})


@router.patch("/{subject_id}/assumptions/{assumption_id}", response_model=ResearchAssumptionResponse)
async def update_research_assumption(
    subject_id: str,
    assumption_id: str,
    data: ResearchAssetReviewUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _get_subject_for_user(subject_id, user, db)
    assumption = await _get_assumption_for_subject(assumption_id, subject, user, db)
    previous_content = assumption.content
    previous_status = assumption.status
    action = _apply_review_update(assumption, data)
    _add_asset_audit(
        db,
        subject=subject,
        user=user,
        asset_type="assumption",
        asset_id=assumption.id,
        action=action,
        previous_content=previous_content,
        new_content=assumption.content,
        previous_status=previous_status,
        new_status=assumption.status,
        review_note=data.review_note.strip() if data.review_note else None,
    )
    await db.commit()
    await db.refresh(assumption)
    evidence_by_id = await _evidence_by_id_for_subject(subject, user, db)
    history_by_asset_id = await _history_by_asset_for_subject(subject, user, db)
    return _assumption_response(assumption, evidence_by_id, history_by_asset_id)


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

from typing import Any

from app.models import (
    ActionRecommendation,
    BusinessEvent,
    DocumentEvidence,
    ResearchAssumption,
    ResearchClaim,
    ResearchSubject,
)
from app.services.llm import chat
from app.services.research_asset_generator import (
    ALLOWED_ACTION_TYPES,
    ALLOWED_LEVELS,
    extract_json_object,
)


def _text(value: Any, limit: int = 800) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def _indexes(value: Any, count: int, limit: int = 4) -> list[int]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(
        item for item in value[:limit] if isinstance(item, int) and 1 <= item <= count
    ))


def _evidence_context(evidence_items: list[DocumentEvidence]) -> str:
    return "\n\n".join(
        f"【E{index}｜{item.location_label}】\n{item.text.strip()[:1200]}"
        for index, item in enumerate(evidence_items[:20], start=1)
        if item.text.strip()
    )


def _normalize_action(item: Any, evidence_items: list[DocumentEvidence]) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    title = _text(item.get("title"), 200)
    rationale = _text(item.get("rationale"), 1000)
    if not title or not rationale:
        return None
    evidence_ids = [
        evidence_items[index - 1].id
        for index in _indexes(item.get("evidence_indexes"), len(evidence_items), 3)
    ]
    action_type = item.get("action_type")
    if not isinstance(action_type, str) or action_type not in ALLOWED_ACTION_TYPES:
        action_type = "document_follow_up"
    risk_level = item.get("risk_level")
    if not isinstance(risk_level, str) or risk_level not in ALLOWED_LEVELS:
        risk_level = "medium"
    return {
        "action_type": action_type,
        "title": title,
        "rationale": rationale,
        "risk_level": risk_level,
        "evidence_ids": evidence_ids,
    }


async def analyze_event_impact(
    subject: ResearchSubject,
    event: BusinessEvent,
    claims: list[ResearchClaim],
    assumptions: list[ResearchAssumption],
    recommendations: list[ActionRecommendation],
    evidence_items: list[DocumentEvidence],
) -> dict[str, Any]:
    if not evidence_items and not claims and not recommendations:
        raise ValueError("当前企业没有可用于影响分析的判断或证据")

    claim_context = "\n".join(
        f"C{index}. {item.content}" for index, item in enumerate(claims[:10], start=1)
    ) or "暂无既有判断"
    assumption_context = "\n".join(
        f"A{index}. {item.content}" for index, item in enumerate(assumptions[:10], start=1)
    ) or "暂无既有假设"
    recommendation_context = "\n".join(
        f"R{index}. {item.title}｜{item.rationale}"
        for index, item in enumerate(recommendations[:10], start=1)
    ) or "暂无既有行动建议"

    system_prompt = """你是银行企业金融事件影响分析智能体。
你必须基于给定的企业事件、既有判断和证据，判断哪些判断或行动建议可能受到影响。
不要直接做授信审批，不要自动修改原有判断，不要给出交易指令。
证据不足时明确列出证据缺口，所有 proposed_actions 都必须等待人工复核。
只输出严格 JSON，不要输出 Markdown。"""
    user_prompt = f"""企业：{subject.company_name}
行业：{subject.industry or '未填写'}

新增事件：
标题：{event.title}
描述：{event.description}

既有判断：
{claim_context}

既有假设：
{assumption_context}

既有行动建议：
{recommendation_context}

证据：
{_evidence_context(evidence_items) or '暂无证据片段'}

请输出：
{{
  "impact_summary": "事件对企业金融状态的影响摘要",
  "affected_claim_indexes": [1],
  "affected_recommendation_indexes": [1],
  "changed_assumptions": ["需要重新核验的假设"],
  "evidence_gaps": ["尚缺少的材料或数据"],
  "proposed_actions": [
    {{
      "action_type": "credit_review|limit_monitoring|collection_monitoring|site_visit|document_follow_up|product_matching|risk_control",
      "title": "待人工确认的下一步动作",
      "rationale": "动作依据",
      "risk_level": "high|medium|low",
      "evidence_indexes": [1]
    }}
  ]
}}"""
    content, _ = await chat(
        messages=[{"role": "user", "content": user_prompt}],
        enable_search=False,
        system_prompt=system_prompt,
    )
    payload = extract_json_object(content)
    return {
        "event_id": event.id,
        "impact_summary": _text(payload.get("impact_summary"), 1200) or "事件影响待人工判断",
        "affected_claim_ids": [
            claims[index - 1].id
            for index in _indexes(payload.get("affected_claim_indexes"), len(claims))
        ],
        "affected_recommendation_ids": [
            recommendations[index - 1].id
            for index in _indexes(payload.get("affected_recommendation_indexes"), len(recommendations))
        ],
        "changed_assumptions": [
            _text(item, 300)
            for item in payload.get("changed_assumptions", [])[:5]
            if _text(item, 300)
        ],
        "evidence_gaps": [
            _text(item, 300)
            for item in payload.get("evidence_gaps", [])[:5]
            if _text(item, 300)
        ],
        "proposed_actions": [
            normalized
            for item in payload.get("proposed_actions", [])[:4]
            if (normalized := _normalize_action(item, evidence_items))
        ],
        "review_required": True,
    }

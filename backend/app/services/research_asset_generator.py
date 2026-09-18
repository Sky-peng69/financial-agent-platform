import json
from typing import Any

from app.models import DocumentEvidence, ResearchSubject
from app.services.llm import chat

MAX_EVIDENCE_ITEMS = 20
MAX_EVIDENCE_CHARS = 12000

ALLOWED_DIRECTIONS = {"positive", "neutral", "negative"}
ALLOWED_LEVELS = {"high", "medium", "low"}
ALLOWED_CATEGORIES = {
    "revenue",
    "margin",
    "cashflow",
    "valuation",
    "policy",
    "competition",
    "business",
    "risk",
}
ALLOWED_NEED_TYPES = {
    "working_capital",
    "equipment",
    "supply_chain",
    "overseas",
    "other",
}
ALLOWED_ACTION_TYPES = {
    "credit_review",
    "limit_monitoring",
    "collection_monitoring",
    "site_visit",
    "document_follow_up",
    "product_matching",
    "risk_control",
}


def _clean_text(value: Any, max_length: int = 1200) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _enum_value(value: Any, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value.strip() in allowed:
        return value.strip()
    return default


def _evidence_indexes(value: Any, evidence_count: int) -> list[int]:
    if not isinstance(value, list):
        return []
    indexes: list[int] = []
    for item in value[:3]:
        if isinstance(item, int) and 1 <= item <= evidence_count and item not in indexes:
            indexes.append(item)
    return indexes


def _relation_indexes(value: Any, max_count: int, max_items: int = 3) -> list[int]:
    if not isinstance(value, list):
        return []
    indexes: list[int] = []
    for item in value[:max_items]:
        if isinstance(item, int) and 1 <= item <= max_count and item not in indexes:
            indexes.append(item)
    return indexes


def extract_json_object(content: str) -> dict[str, Any]:
    json_text = content.strip()
    if json_text.startswith("```"):
        json_text = json_text.strip("`")
        if json_text.startswith("json"):
            json_text = json_text[4:]
    start = json_text.find("{")
    end = json_text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("模型未返回可解析的 JSON")
    return json.loads(json_text[start:end + 1])


def normalize_research_assets(
    payload: dict[str, Any],
    evidence_count: int = MAX_EVIDENCE_ITEMS,
) -> dict[str, Any]:
    claims = []
    for item in payload.get("claims", [])[:3]:
        content = _clean_text(item.get("content"))
        if not content:
            continue
        indexes = _evidence_indexes(item.get("evidence_indexes"), evidence_count)
        claims.append({
            "content": content,
            "direction": _enum_value(item.get("direction"), ALLOWED_DIRECTIONS, "neutral"),
            "confidence_level": _enum_value(item.get("confidence_level"), ALLOWED_LEVELS, "medium"),
            "evidence_strength": _enum_value(item.get("evidence_strength"), ALLOWED_LEVELS, "medium"),
            "status": "needs_review",
            "evidence_indexes": indexes,
            "verification_status": "cited" if indexes else "needs_review",
        })

    assumptions = []
    for item in payload.get("assumptions", [])[:5]:
        content = _clean_text(item.get("content"))
        if not content:
            continue
        indexes = _evidence_indexes(item.get("evidence_indexes"), evidence_count)
        assumptions.append({
            "content": content,
            "category": _enum_value(item.get("category"), ALLOWED_CATEGORIES, "business"),
            "confidence_level": _enum_value(item.get("confidence_level"), ALLOWED_LEVELS, "medium"),
            "status": "active",
            "evidence_indexes": indexes,
            "verification_status": "cited" if indexes else "needs_review",
        })

    challenges = []
    for item in payload.get("challenges", [])[:3]:
        question = _clean_text(item.get("question"))
        if not question:
            continue
        challenges.append({
            "question": question,
            "risk_level": _enum_value(item.get("risk_level"), ALLOWED_LEVELS, "medium"),
            "suggested_action": _clean_text(item.get("suggested_action"), 500) or None,
        })

    memo_payload = payload.get("decision_memo") or {}
    decision_memo = {
        "current_conclusion": _clean_text(memo_payload.get("current_conclusion")),
        "key_basis": _clean_text(memo_payload.get("key_basis"), 1000) or None,
        "biggest_uncertainty": _clean_text(memo_payload.get("biggest_uncertainty"), 1000) or None,
        "suggested_action": _clean_text(memo_payload.get("suggested_action"), 800) or None,
        "review_status": "ai_draft",
    }

    action_recommendations = []
    for item in payload.get("action_recommendations", [])[:4]:
        title = _clean_text(item.get("title"), 200)
        rationale = _clean_text(item.get("rationale"), 1200)
        if not title or not rationale:
            continue
        action_recommendations.append({
            "action_type": _enum_value(
                item.get("action_type"),
                ALLOWED_ACTION_TYPES,
                "document_follow_up",
            ),
            "title": title,
            "rationale": rationale,
            "risk_level": _enum_value(item.get("risk_level"), ALLOWED_LEVELS, "medium"),
            "evidence_indexes": _evidence_indexes(item.get("evidence_indexes"), evidence_count),
            "related_claim_indexes": _relation_indexes(item.get("related_claim_indexes"), len(claims)),
            "related_assumption_indexes": _relation_indexes(
                item.get("related_assumption_indexes"),
                len(assumptions),
            ),
            "status": "needs_review",
        })

    financing_needs = []
    for item in payload.get("financing_needs", [])[:4]:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"), 200)
        description = _clean_text(item.get("description"), 1200)
        if not title or not description:
            continue
        financing_needs.append({
            "need_type": _enum_value(item.get("need_type"), ALLOWED_NEED_TYPES, "other"),
            "title": title,
            "description": description,
            "amount_text": _clean_text(item.get("amount_text"), 100) or None,
            "urgency": _enum_value(item.get("urgency"), ALLOWED_LEVELS, "medium"),
            "evidence_indexes": _evidence_indexes(item.get("evidence_indexes"), evidence_count),
            "status": "needs_review",
        })

    if not action_recommendations:
        fallback_title = decision_memo["suggested_action"] or "补充核验关键不确定性"
        fallback_rationale = (
            decision_memo["biggest_uncertainty"]
            or "当前材料不足以直接形成金融动作，需由人工补充核验。"
        )
        action_recommendations.append({
            "action_type": "document_follow_up",
            "title": _clean_text(fallback_title, 200),
            "rationale": _clean_text(fallback_rationale, 1200),
            "risk_level": "medium",
            "evidence_indexes": [],
            "related_claim_indexes": [],
            "related_assumption_indexes": [],
            "status": "needs_review",
        })

    if not claims or not assumptions or not challenges or not decision_memo["current_conclusion"]:
        raise ValueError("模型返回的判断资产不完整")

    return {
        "claims": claims,
        "assumptions": assumptions,
        "challenges": challenges,
        "decision_memo": decision_memo,
        "action_recommendations": action_recommendations,
        "financing_needs": financing_needs,
    }


def _build_evidence_context(evidence_items: list[DocumentEvidence]) -> str:
    blocks: list[str] = []
    remaining = MAX_EVIDENCE_CHARS
    for index, item in enumerate(evidence_items[:MAX_EVIDENCE_ITEMS], start=1):
        text = item.text.strip()
        if not text:
            continue
        block = f"【E{index}｜{item.location_label}】\n{text}"
        excerpt = block[:remaining]
        blocks.append(excerpt)
        remaining -= len(excerpt)
        if remaining <= 0:
            break
    return "\n\n".join(blocks)


async def generate_research_assets(
    subject: ResearchSubject,
    evidence_items: list[DocumentEvidence],
) -> dict[str, Any]:
    evidence_context = _build_evidence_context(evidence_items)
    if not evidence_context:
        raise ValueError("没有可用于分析的材料文本")

    system_prompt = """你是银行企业金融尽调智能体。
你的任务不是写一篇报告，而是把企业材料沉淀成可复核的事实、风险判断、融资需求和金融行动建议。

只允许根据用户提供的材料和研究对象信息输出；证据不足时降低置信度，不要编造数字、事实或来源。
每条判断、假设和行动建议都要用 evidence_indexes 标出对应的 E 编号；找不到直接证据时可以留空。
融资需求只能记录材料明确支持或需要人工核验的需求，不得推算金额或直接形成授信结论。
行动建议必须是“下一步可由银行人员执行并复核的动作”，不能自动授信、自动放款、自动调额或自动交易。
必须只输出 JSON，不要使用 Markdown，不要解释处理过程。"""

    user_prompt = f"""请基于以下企业和材料片段，生成结构化企业金融尽调资产。

研究对象：
- 公司：{subject.company_name}
- 股票代码：{subject.ticker or "未填写"}
- 行业：{subject.industry or "未填写"}
- 当前判断：{subject.current_view or "尚未形成"}

材料片段：
{evidence_context}

请输出严格 JSON：
{{
  "claims": [
    {{
      "content": "一句完整、可被反驳的核心判断",
      "direction": "positive|neutral|negative",
      "confidence_level": "high|medium|low",
      "evidence_strength": "high|medium|low",
      "evidence_indexes": [1]
    }}
  ],
  "assumptions": [
    {{
      "content": "支撑判断成立的关键假设",
      "category": "revenue|margin|cashflow|valuation|policy|competition|business|risk",
      "confidence_level": "high|medium|low",
      "evidence_indexes": [1]
    }}
  ],
  "challenges": [
    {{
      "question": "最值得投研人员追问的反方问题",
      "risk_level": "high|medium|low",
      "suggested_action": "下一步核验动作"
    }}
  ],
  "decision_memo": {{
    "current_conclusion": "当前可复核结论",
    "key_basis": "关键依据",
    "biggest_uncertainty": "最大不确定性",
    "suggested_action": "下一步核验或服务动作"
  }},
  "financing_needs": [
    {{
      "need_type": "working_capital|equipment|supply_chain|overseas|other",
      "title": "企业可能存在的融资或金融服务需求",
      "description": "需求依据；证据不足时明确写待核验",
      "amount_text": "材料明确披露的金额文本，未知时留空",
      "urgency": "high|medium|low",
      "evidence_indexes": [1]
    }}
  ],
  "action_recommendations": [
    {{
      "action_type": "credit_review|limit_monitoring|collection_monitoring|site_visit|document_follow_up|product_matching|risk_control",
      "title": "银行人员下一步要做的动作",
      "rationale": "动作依据和需要关注的风险/机会",
      "risk_level": "high|medium|low",
      "evidence_indexes": [1],
      "related_claim_indexes": [1],
      "related_assumption_indexes": [1]
    }}
  ]
}}"""

    content, _ = await chat(
        messages=[{"role": "user", "content": user_prompt}],
        enable_search=False,
        system_prompt=system_prompt,
    )
    return normalize_research_assets(extract_json_object(content), len(evidence_items))

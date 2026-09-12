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


def _clean_text(value: Any, max_length: int = 1200) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _enum_value(value: Any, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value.strip() in allowed:
        return value.strip()
    return default


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


def normalize_research_assets(payload: dict[str, Any]) -> dict[str, Any]:
    claims = []
    for item in payload.get("claims", [])[:3]:
        content = _clean_text(item.get("content"))
        if not content:
            continue
        claims.append({
            "content": content,
            "direction": _enum_value(item.get("direction"), ALLOWED_DIRECTIONS, "neutral"),
            "confidence_level": _enum_value(item.get("confidence_level"), ALLOWED_LEVELS, "medium"),
            "evidence_strength": _enum_value(item.get("evidence_strength"), ALLOWED_LEVELS, "medium"),
            "status": "needs_review",
        })

    assumptions = []
    for item in payload.get("assumptions", [])[:5]:
        content = _clean_text(item.get("content"))
        if not content:
            continue
        assumptions.append({
            "content": content,
            "category": _enum_value(item.get("category"), ALLOWED_CATEGORIES, "business"),
            "confidence_level": _enum_value(item.get("confidence_level"), ALLOWED_LEVELS, "medium"),
            "status": "active",
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

    if not claims or not assumptions or not challenges or not decision_memo["current_conclusion"]:
        raise ValueError("模型返回的判断资产不完整")

    return {
        "claims": claims,
        "assumptions": assumptions,
        "challenges": challenges,
        "decision_memo": decision_memo,
    }


def _build_evidence_context(evidence_items: list[DocumentEvidence]) -> str:
    blocks: list[str] = []
    remaining = MAX_EVIDENCE_CHARS
    for item in evidence_items[:MAX_EVIDENCE_ITEMS]:
        text = item.text.strip()
        if not text:
            continue
        block = f"【{item.location_label}】\n{text}"
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

    system_prompt = """你是证券公司/基金公司的 A 股投研助理。
你的任务不是写一篇报告，而是把材料沉淀成可复核的研究判断资产。

只允许根据用户提供的材料和研究对象信息输出；证据不足时降低置信度，不要编造数字、事实或来源。
必须只输出 JSON，不要使用 Markdown，不要解释处理过程。"""

    user_prompt = f"""请基于以下研究对象和材料片段，生成结构化判断资产。

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
      "evidence_strength": "high|medium|low"
    }}
  ],
  "assumptions": [
    {{
      "content": "支撑判断成立的关键假设",
      "category": "revenue|margin|cashflow|valuation|policy|competition|business|risk",
      "confidence_level": "high|medium|low"
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
    "suggested_action": "下一步研究动作"
  }}
}}"""

    content, _ = await chat(
        messages=[{"role": "user", "content": user_prompt}],
        enable_search=False,
        system_prompt=system_prompt,
    )
    return normalize_research_assets(extract_json_object(content))

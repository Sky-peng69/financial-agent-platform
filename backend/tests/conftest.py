"""测试基础设施：测试数据库、ASGI 客户端、认证与 LLM mock。

运行前提（一次性）：
    docker exec agent-db-1 createdb -U finagent finagent_test
    pip install -r requirements-dev.txt

环境变量在导入 app 之前设置（app.core.config.settings 在导入时实例化）：
    DATABASE_URL 默认指向本机 docker Postgres 的 finagent_test 库
    STORAGE_PATH  默认使用临时目录，测试文件不落仓库
    DEBUG         关闭 SQL echo，保持测试输出可读

LLM 调用（chat）全部由测试 monkeypatch 替换，不产生真实 API 消耗。
"""

import atexit
import json
import os
import shutil
import tempfile
from pathlib import Path

_TEST_STORAGE = tempfile.mkdtemp(prefix="yijin-cc-storage-")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://finagent:finagent_dev@localhost:5433/finagent_test",
)
os.environ.setdefault("STORAGE_PATH", _TEST_STORAGE)
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-never-called")

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _cleanup_storage() -> None:
    shutil.rmtree(_TEST_STORAGE, ignore_errors=True)


atexit.register(_cleanup_storage)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def initialized_db():
    """重建一次测试库表结构，保证测试可重复运行。"""
    import app.models  # noqa: F401  确保所有表在 Base.metadata 上注册后再 drop/create
    from app.core.database import Base, engine, init_db

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(initialized_db):
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_session(initialized_db):
    """直连数据库会话，用于造旧接口的存量数据（任务、报告）。"""
    from app.core.database import async_session

    async with async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# 认证辅助
# ---------------------------------------------------------------------------


async def register_user(client: httpx.AsyncClient, email: str, password: str = "test-pass-123") -> dict:
    response = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# LLM mock：与 app/services 中 chat 的真实输出契约保持一致
# ---------------------------------------------------------------------------

FAKE_ASSET_PAYLOAD = {
    "claims": [
        {
            "content": "公司储能业务保持高增长，是未来两年收入的主要增量来源",
            "direction": "positive",
            "confidence_level": "high",
            "evidence_strength": "medium",
            "evidence_indexes": [2],
        },
        {
            "content": "原材料价格波动对毛利率构成压力",
            "direction": "negative",
            "confidence_level": "medium",
            "evidence_strength": "low",
            "evidence_indexes": [],
        },
    ],
    "assumptions": [
        {
            "content": "储能电池需求增速维持在 30% 以上",
            "category": "business",
            "confidence_level": "medium",
            "evidence_indexes": [2],
        }
    ],
    "challenges": [
        {
            "question": "储能业务高增长的可持续性是否已被下游订单验证？",
            "risk_level": "high",
            "suggested_action": "核验近两季度储能业务新签订单",
        }
    ],
    "decision_memo": {
        "current_conclusion": "公司基本面稳健，储能业务提供增量，但毛利率承压需持续跟踪",
        "key_basis": "第 2 页公司概况与业务数据",
        "biggest_uncertainty": "储能订单兑现节奏",
        "suggested_action": "补充核验储能订单与成本数据",
    },
    "financing_needs": [
        {
            "need_type": "working_capital",
            "title": "补充经营周转资金",
            "description": "订单增长和回款节奏需要进一步核验，可能存在阶段性营运资金需求",
            "amount_text": "待核验",
            "urgency": "medium",
            "evidence_indexes": [2],
        }
    ],
    "action_recommendations": [
        {
            "action_type": "site_visit",
            "title": "实地走访核实储能产线产能利用率",
            "rationale": "第 2 页披露储能业务高增长，需现场核验产能与订单匹配度",
            "risk_level": "medium",
            "evidence_indexes": [2],
            "related_claim_indexes": [1],
            "related_assumption_indexes": [1],
        }
    ],
}

FAKE_IMPACT_PAYLOAD = {
    "impact_summary": "储能大客户订单取消可能拖累收入预期，相关判断与行动建议需要重新核验",
    "affected_claim_indexes": [1],
    "affected_recommendation_indexes": [1],
    "changed_assumptions": ["储能电池需求增速假设需要下调重估"],
    "evidence_gaps": ["缺少最新季度订单与出货数据", "缺少大客户集中度明细"],
    "proposed_actions": [
        {
            "action_type": "credit_review",
            "title": "重新评估授信额度的收入假设基础",
            "rationale": "核心客户订单变化直接影响收入判断，需在复核后重新评估",
            "risk_level": "high",
            "evidence_indexes": [1],
        }
    ],
}


def install_llm_mocks(monkeypatch, asset_payload: dict | None = None, impact_payload: dict | None = None) -> None:
    """替换两个服务中的 chat 调用，返回可控的结构化 JSON。"""

    async def fake_asset_chat(messages=None, **kwargs):
        return json.dumps(asset_payload or FAKE_ASSET_PAYLOAD, ensure_ascii=False), None

    async def fake_impact_chat(messages=None, **kwargs):
        return json.dumps(impact_payload or FAKE_IMPACT_PAYLOAD, ensure_ascii=False), None

    monkeypatch.setattr("app.services.research_asset_generator.chat", fake_asset_chat)
    monkeypatch.setattr("app.services.event_impact_analyzer.chat", fake_impact_chat)


async def failing_chat(runtime: bool = True):
    """返回一个按需抛错的 chat 替身：RuntimeError → 503，ValueError → 502。"""

    async def fake_chat(messages=None, **kwargs):
        if runtime:
            raise RuntimeError("模拟模型服务不可用")
        raise ValueError("模拟模型返回不可解析的结构")

    return fake_chat


# ---------------------------------------------------------------------------
# 尽调闭环的公共搭建：用户 + 研究对象 + PDF 证据
# ---------------------------------------------------------------------------


async def setup_subject_with_evidence(client: httpx.AsyncClient, email: str):
    """注册用户、创建研究对象、上传样例 PDF，返回 (user, token, headers, subject, file, evidence)。"""
    user = await register_user(client, email)
    token = user["access_token"]
    headers = auth_headers(token)

    response = await client.post(
        "/api/research-subjects",
        json={"company_name": "测试制造股份有限公司", "ticker": "600000", "industry": "制造业"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    subject = response.json()

    pdf_bytes = (FIXTURES_DIR / "sample.pdf").read_bytes()
    response = await client.post(
        "/api/files",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={"research_subject_id": subject["id"]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    uploaded_file = response.json()

    response = await client.get(f"/api/files/{uploaded_file['id']}/evidence", headers=headers)
    assert response.status_code == 200, response.text
    evidence = response.json()
    return user, token, headers, subject, uploaded_file, evidence

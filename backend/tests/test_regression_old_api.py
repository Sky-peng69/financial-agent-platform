"""旧接口非回归测试。

覆盖：认证、任务（search_references 新列）、文件（无研究对象路径）、
判断/假设/挑战/备忘录（含新增字段的响应）、报告列表与下载、Agent 目录、健康检查。
"""

import json

from tests.conftest import (
    FIXTURES_DIR,
    register_user,
    setup_subject_with_evidence,
)


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_auth_login_flow(client):
    await register_user(client, "login-check@test.com")
    response = await client.post(
        "/api/auth/login", json={"email": "login-check@test.com", "password": "test-pass-123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "login-check@test.com"

    response = await client.post(
        "/api/auth/login", json={"email": "login-check@test.com", "password": "wrong-pass"}
    )
    assert response.status_code == 401

    # 重复注册 → 400
    response = await client.post(
        "/api/auth/register",
        json={"email": "login-check@test.com", "password": "test-pass-123"},
    )
    assert response.status_code == 400


async def test_task_interface_with_search_references(client, db_session):
    """旧任务接口：search_references 新增列不影响创建/读取。"""
    from app.models import Task, TaskStatus

    user = await register_user(client, "task-check@test.com")
    db_session.add(
        Task(
            user_id=user["user"]["id"],
            agent_name="industry-researcher",
            title="行业分析任务",
            input_data="分析新能源行业",
            output_data="分析结果",
            search_references=json.dumps(
                [{"name": "示例来源", "url": "https://example.com", "snippet": "摘要"}],
                ensure_ascii=False,
            ),
            status=TaskStatus.COMPLETED,
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {user['access_token']}"}
    response = await client.get("/api/tasks", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["search_references"] is not None
    assert "example.com" in tasks[0]["search_references"]

    response = await client.get(f"/api/tasks/{tasks[0]['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["agent_name"] == "industry-researcher"

    # 无认证 → 403（HTTPBearer 缺凭证的 FastAPI 标准行为）
    response = await client.get("/api/tasks")
    assert response.status_code == 403


async def test_file_upload_without_subject(client):
    """旧文件上传路径：不挂研究对象也照常解析出页码级证据。"""
    user = await register_user(client, "file-check@test.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    pdf_bytes = (FIXTURES_DIR / "sample.pdf").read_bytes()

    response = await client.post(
        "/api/files",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    uploaded = response.json()
    assert uploaded["research_subject_id"] is None
    assert uploaded["status"] == "parsed"

    response = await client.get(f"/api/files/{uploaded['id']}/evidence", headers=headers)
    assert response.status_code == 200
    evidence = response.json()
    assert len(evidence) == 3
    assert [item["page_number"] for item in evidence] == [1, 2, 3]
    assert all(item["text"] for item in evidence)

    # 下载内容与上传一致
    response = await client.get(f"/api/files/{uploaded['id']}/download", headers=headers)
    assert response.status_code == 200
    assert response.content == pdf_bytes

    # 非法类型 → 400
    response = await client.post(
        "/api/files",
        files={"file": ("evil.exe", b"MZ-not-a-pdf", "application/octet-stream")},
        headers=headers,
    )
    assert response.status_code == 400

    # 超大小限制 → 413（PDF 头合法但超过 20MB）
    oversized = pdf_bytes + b"\0" * (20 * 1024 * 1024)
    response = await client.post(
        "/api/files",
        files={"file": ("huge.pdf", oversized, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 413


async def test_claim_assumption_flows(client, monkeypatch):
    """判断/假设的创建、编辑、确认、驳回与审计历史（含新增字段）。"""
    from tests.conftest import install_llm_mocks

    install_llm_mocks(monkeypatch)
    _, token, headers, subject, _, _ = await setup_subject_with_evidence(
        client, "claim-flow@test.com"
    )

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/claims",
        json={"content": "手工创建的判断", "direction": "positive"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    claim = response.json()
    assert claim["verification_status"] == "needs_review"
    assert claim["evidence_items"] == []

    # 编辑内容 → 审计动作 edited
    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/claims/{claim['id']}",
        json={"content": "手工创建并编辑后的判断"},
        headers=headers,
    )
    assert response.status_code == 200
    edited = response.json()
    assert edited["content"] == "手工创建并编辑后的判断"
    edit_audit = next(item for item in edited["history"] if item["action"] == "edited")
    assert edit_audit["previous_content"] == "手工创建的判断"
    assert edit_audit["new_content"] == "手工创建并编辑后的判断"

    # 确认 → 审计动作 confirmed，时间戳落库
    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/claims/{claim['id']}",
        json={"status": "confirmed", "review_note": "人工核对通过"},
        headers=headers,
    )
    assert response.status_code == 200
    confirmed = response.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["reviewed_at"] is not None
    assert any(item["action"] == "confirmed" for item in confirmed["history"])

    # 假设：创建与确认
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/assumptions",
        json={"content": "行业增速假设", "category": "business"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assumption = response.json()
    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/assumptions/{assumption['id']}",
        json={"status": "confirmed", "review_note": "依据充分"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert any(item["action"] == "confirmed" for item in response.json()["history"])

    # 工作区聚合：判断与假设都带新增字段返回
    response = await client.get(
        f"/api/research-subjects/{subject['id']}/workspace", headers=headers
    )
    workspace = response.json()
    assert len(workspace["claims"]) == 1
    assert len(workspace["assumptions"]) == 1
    assert workspace["evidence_count"] == 3


async def test_challenge_and_memo_flows(client, monkeypatch):
    """挑战与决策备忘录接口非回归。"""
    from tests.conftest import install_llm_mocks

    install_llm_mocks(monkeypatch)
    _, token, headers, subject, _, _ = await setup_subject_with_evidence(
        client, "challenge-flow@test.com"
    )

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/challenges",
        json={"question": "收入增速是否可持续？", "risk_level": "high"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    challenge = response.json()
    assert challenge["claim_id"] is None

    # 挑战指向他人/不存在的判断 → 404
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/challenges",
        json={"question": "越权挑战", "claim_id": "不存在的判断ID"},
        headers=headers,
    )
    assert response.status_code == 404

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/decision-memos",
        json={"current_conclusion": "手工备忘录结论", "key_basis": "依据"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    memo = response.json()
    assert memo["review_status"] == "ai_draft"

    response = await client.get(
        f"/api/research-subjects/{subject['id']}/workspace", headers=headers
    )
    workspace = response.json()
    assert len(workspace["challenges"]) == 1
    assert len(workspace["decision_memos"]) == 1


async def test_report_list_and_download(client, db_session):
    """报告列表（旧对象）与下载契约非回归。"""
    from app.models import ResearchReport

    user = await register_user(client, "report-check@test.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    response = await client.post(
        "/api/research-subjects", json={"company_name": "报告测试公司"}, headers=headers
    )
    subject_id = response.json()["id"]

    from app.services.report_builder import storage

    report_id = "report-regression-001"
    storage_key = f"reports/{user['user']['id']}/{report_id}/报告.md"
    storage.save(storage_key, "# 报告内容".encode("utf-8"))
    db_session.add(
        ResearchReport(
            id=report_id,
            user_id=user["user"]["id"],
            research_subject_id=subject_id,
            title="回归测试报告",
            report_style="institutional",
            content_markdown="# 报告内容",
            file_manifest=json.dumps(
                [
                    {
                        "format": "md",
                        "filename": "回归测试报告.md",
                        "storage_key": storage_key,
                        "content_type": "text/markdown; charset=utf-8",
                    }
                ],
                ensure_ascii=False,
            ),
            review_status="ai_draft",
        )
    )
    await db_session.commit()

    response = await client.get(
        f"/api/research-subjects/{subject_id}/reports", headers=headers
    )
    assert response.status_code == 200, response.text
    reports = response.json()
    assert len(reports) == 1
    assert reports[0]["title"] == "回归测试报告"
    assert reports[0]["review_status"] == "ai_draft"
    assert reports[0]["files"][0]["format"] == "md"

    response = await client.get(f"/api/reports/{report_id}/download/md", headers=headers)
    assert response.status_code == 200
    assert response.content.decode("utf-8") == "# 报告内容"

    # 不存在的格式 → 404
    response = await client.get(f"/api/reports/{report_id}/download/pdf", headers=headers)
    assert response.status_code == 404

    # 跨用户下载 → 404
    token_b = (await register_user(client, "report-b@test.com"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    response = await client.get(f"/api/reports/{report_id}/download/md", headers=headers_b)
    assert response.status_code == 404


async def test_agent_catalog(client):
    """Agent 目录接口非回归。"""
    response = await client.get("/api/agents")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert "macro-economy-analyst" in names
    assert "report-synthesizer" in names

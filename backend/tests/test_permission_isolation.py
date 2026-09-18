"""跨用户权限隔离测试。

验收红线：用户 B 不能读取/操作用户 A 的企业、证据、事件、建议或审计历史；
所有越权访问返回 404，不泄露资源存在性。
"""

from tests.conftest import (
    install_llm_mocks,
    register_user,
    setup_subject_with_evidence,
)


async def _user_a_with_full_assets(client, monkeypatch, email):
    """用户 A：研究对象 + PDF 证据 + 尽调资产 + 事件。"""
    install_llm_mocks(monkeypatch)
    user_a, token_a, headers_a, subject_a, file_a, evidence_a = await setup_subject_with_evidence(
        client, email
    )
    response = await client.post(
        f"/api/research-subjects/{subject_a['id']}/generate-assets", headers=headers_a
    )
    assert response.status_code == 200
    workspace = response.json()
    recommendation_a = workspace["action_recommendations"][0]
    claim_a = workspace["claims"][0]
    financing_need_a = workspace["financing_needs"][0]
    response = await client.post(
        f"/api/research-subjects/{subject_a['id']}/events",
        json={"title": "A 的企业事件", "description": "事件描述"},
        headers=headers_a,
    )
    event_a = response.json()
    return {
        "user": user_a,
        "token": token_a,
        "headers": headers_a,
        "subject": subject_a,
        "file": file_a,
        "evidence": evidence_a,
        "recommendation": recommendation_a,
        "claim": claim_a,
        "financing_need": financing_need_a,
        "event": event_a,
    }


async def test_cross_user_subject_and_workspace_404(client, monkeypatch):
    a = await _user_a_with_full_assets(client, monkeypatch, "iso-subject-a@test.com")
    token_b = (await register_user(client, "iso-subject-b@test.com"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # B 读取 A 的研究对象 → 404
    for path in (
        f"/api/research-subjects/{a['subject']['id']}",
        f"/api/research-subjects/{a['subject']['id']}/workspace",
        f"/api/research-subjects/{a['subject']['id']}/reports",
    ):
        response = await client.get(path, headers=headers_b)
        assert response.status_code == 404, path

    # B 向 A 的研究对象写入事件 → 404
    response = await client.post(
        f"/api/research-subjects/{a['subject']['id']}/events",
        json={"title": "B 尝试写入", "description": "不应成功"},
        headers=headers_b,
    )
    assert response.status_code == 404
    response = await client.get(
        f"/api/research-subjects/{a['subject']['id']}/events", headers=headers_b
    )
    assert response.status_code == 404

    # B 的列表看不到 A 的任何数据
    response = await client.get("/api/research-subjects", headers=headers_b)
    assert response.json() == []


async def test_cross_user_evidence_and_file_404(client, monkeypatch):
    a = await _user_a_with_full_assets(client, monkeypatch, "iso-files-a@test.com")
    token_b = (await register_user(client, "iso-files-b@test.com"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # B 读取 A 的文件证据/下载 A 的文件 → 404
    response = await client.get(
        f"/api/files/{a['file']['id']}/evidence", headers=headers_b
    )
    assert response.status_code == 404
    response = await client.get(f"/api/files/{a['file']['id']}/download", headers=headers_b)
    assert response.status_code == 404

    # B 上传文件挂到 A 的研究对象 → 404
    from tests.conftest import FIXTURES_DIR

    pdf_bytes = (FIXTURES_DIR / "sample.pdf").read_bytes()
    response = await client.post(
        "/api/files",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={"research_subject_id": a["subject"]["id"]},
        headers=headers_b,
    )
    assert response.status_code == 404

    # B 自己的文件列表为空
    response = await client.get("/api/files", headers=headers_b)
    assert response.json() == []


async def test_cross_user_recommendation_and_audit_404(client, monkeypatch):
    a = await _user_a_with_full_assets(client, monkeypatch, "iso-rec-a@test.com")
    token_b = (await register_user(client, "iso-rec-b@test.com"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # B 在 A 的研究对象下创建行动建议 → 404
    response = await client.post(
        f"/api/research-subjects/{a['subject']['id']}/action-recommendations",
        json={
            "action_type": "site_visit",
            "title": "B 尝试创建",
            "rationale": "不应成功",
            "status": "needs_review",
        },
        headers=headers_b,
    )
    assert response.status_code == 404

    # B 复核 A 的行动建议 → 404（即使带上 A 的 subject id 与建议 id）
    response = await client.patch(
        f"/api/research-subjects/{a['subject']['id']}/action-recommendations/{a['recommendation']['id']}",
        json={"status": "confirmed", "review_note": "B 尝试确认"},
        headers=headers_b,
    )
    assert response.status_code == 404

    # B 复核 A 的判断 → 404
    response = await client.patch(
        f"/api/research-subjects/{a['subject']['id']}/claims/{a['claim']['id']}",
        json={"status": "confirmed"},
        headers=headers_b,
    )
    assert response.status_code == 404

    # B 读取/复核 A 的融资需求 → 404
    response = await client.get(
        f"/api/research-subjects/{a['subject']['id']}/financing-needs", headers=headers_b
    )
    assert response.status_code == 404
    response = await client.patch(
        f"/api/research-subjects/{a['subject']['id']}/financing-needs/{a['financing_need']['id']}",
        json={"status": "confirmed", "review_note": "B 尝试确认"},
        headers=headers_b,
    )
    assert response.status_code == 404


async def test_cross_user_event_impact_404(client, monkeypatch):
    a = await _user_a_with_full_assets(client, monkeypatch, "iso-event-a@test.com")
    token_b = (await register_user(client, "iso-event-b@test.com"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # B 对 A 的事件做影响分析 → 404
    response = await client.post(
        f"/api/research-subjects/{a['subject']['id']}/events/{a['event']['id']}/impact-preview",
        headers=headers_b,
    )
    assert response.status_code == 404
    response = await client.get(
        f"/api/research-subjects/{a['subject']['id']}/events/{a['event']['id']}/impact-previews",
        headers=headers_b,
    )
    assert response.status_code == 404

    # B 建了自己的对象和事件后，拿 B 的事件 id 配 A 的 subject id → 404（不泄露）
    response = await client.post(
        "/api/research-subjects", json={"company_name": "B 的公司"}, headers=headers_b
    )
    subject_b_id = response.json()["id"]
    response = await client.post(
        f"/api/research-subjects/{subject_b_id}/events",
        json={"title": "B 的事件", "description": "描述"},
        headers=headers_b,
    )
    event_b_id = response.json()["id"]
    response = await client.post(
        f"/api/research-subjects/{a['subject']['id']}/events/{event_b_id}/impact-preview",
        headers=headers_b,
    )
    assert response.status_code == 404


async def test_cross_user_task_404(client, monkeypatch, db_session):
    """旧接口任务对象的跨用户隔离。"""
    a = await _user_a_with_full_assets(client, monkeypatch, "iso-task-a@test.com")
    from app.models import Task, TaskStatus

    db_session.add(
        Task(
            user_id=a["user"]["user"]["id"],
            agent_name="macro-economy-analyst",
            title="A 的分析任务",
            input_data="输入",
            output_data="输出",
            search_references="[]",
            status=TaskStatus.COMPLETED,
        )
    )
    await db_session.commit()

    token_b = (await register_user(client, "iso-task-b@test.com"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = await client.get("/api/tasks", headers=headers_b)
    assert response.json() == []

    # 从 A 的视角拿到任务 id，再用 B 的身份访问 → 404
    response = await client.get("/api/tasks", headers=a["headers"])
    task_a = response.json()[0]
    response = await client.get(f"/api/tasks/{task_a['id']}", headers=headers_b)
    assert response.status_code == 404


async def test_owner_keeps_full_access(client, monkeypatch):
    """所有者自己访问全部正常，确认隔离逻辑没有误伤。"""
    a = await _user_a_with_full_assets(client, monkeypatch, "iso-owner-a@test.com")
    response = await client.get(
        f"/api/research-subjects/{a['subject']['id']}/workspace", headers=a["headers"]
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["business_events"]) == 1
    assert len(body["action_recommendations"]) == 1
    assert len(body["financing_needs"]) == 1
    response = await client.get(
        f"/api/research-subjects/{a['subject']['id']}/financing-needs", headers=a["headers"]
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    response = await client.get(f"/api/files/{a['file']['id']}/evidence", headers=a["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 3

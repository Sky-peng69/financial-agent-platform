"""企业金融尽调闭环端到端测试。

链路：研究对象 → PDF 证据 → 结构化行动建议 → 企业事件 → 事件影响预览
      → 待复核动作（仅人工转换）→ 确认/驳回 → 审计记录。
"""

import pytest

from tests.conftest import (
    FIXTURES_DIR,
    install_llm_mocks,
    failing_chat,
    register_user,
    setup_subject_with_evidence,
)


def _history_actions(recommendation: dict) -> list[str]:
    return [item["action"] for item in recommendation.get("history", [])]


async def test_full_diligence_chain(client, monkeypatch):
    """验收闭环：证据 → 资产 → 事件 → 影响预览 → 人工转建议 → 复核 → 审计。"""
    install_llm_mocks(monkeypatch)
    user, token, headers, subject, uploaded_file, evidence = await setup_subject_with_evidence(
        client, "chain-user@test.com"
    )
    evidence_ids = {item["id"] for item in evidence}

    # 1. 生成结构化尽调资产（含行动建议）
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/generate-assets", headers=headers
    )
    assert response.status_code == 200, response.text
    workspace = response.json()

    assert len(workspace["claims"]) == 2
    assert len(workspace["assumptions"]) == 1
    assert len(workspace["challenges"]) == 1
    assert len(workspace["decision_memos"]) == 1
    assert workspace["evidence_count"] == len(evidence) == 3

    # 判断与证据绑定：evidence_ids 只能指向当前研究对象自己的证据
    for claim in workspace["claims"]:
        assert set(claim["evidence_ids"]) <= evidence_ids
        assert claim["status"] == "needs_review"

    # 行动建议：状态 needs_review，生成即落审计
    recommendations = workspace["action_recommendations"]
    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation["status"] == "needs_review"
    assert set(recommendation["evidence_ids"]) <= evidence_ids
    assert "generated" in _history_actions(recommendation)
    generated_audit = next(
        item for item in recommendation["history"] if item["action"] == "generated"
    )
    assert generated_audit["new_status"] == "needs_review"
    assert generated_audit["previous_content"] is None
    assert generated_audit["new_content"] is not None

    # 建议通过 id 关联判断（判断列表按 updated_at 排序，不能用下标取）
    cited_claim = next(
        claim
        for claim in workspace["claims"]
        if claim["id"] == recommendation["related_claim_ids"][0]
    )
    assert cited_claim["verification_status"] == "cited", "模型引用证据的判断应为已引用状态"

    # 研究对象总览被生成结果更新
    assert subject["current_view"] != workspace["subject"]["current_view"]
    assert workspace["subject"]["confidence_level"] is not None

    # 2. 录入企业事件
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/events",
        json={
            "title": "储能大客户订单取消",
            "description": "公司披露某储能大客户取消后续两年部分订单",
            "source_type": "announcement",
            "source_reference": "巨潮公告示例链接",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    event = response.json()
    assert event["research_subject_id"] == subject["id"]
    assert event["status"] == "active"

    # 3. 事件影响预览：返回受影响判断/建议、证据缺口与新动作，但不落库
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/events/{event['id']}/impact-preview",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["event_id"] == event["id"]
    # 受影响判断索引基于查询时的排序（updated_at 相同则不保证顺序），只校验 id 归属
    claim_ids = {claim["id"] for claim in workspace["claims"]}
    assert len(preview["affected_claim_ids"]) == 1
    assert set(preview["affected_claim_ids"]) <= claim_ids
    assert preview["affected_recommendation_ids"] == [recommendation["id"]]
    assert preview["evidence_gaps"], "事件影响分析应指出证据缺口"
    assert preview["proposed_actions"], "事件影响分析应给出待复核新动作"
    proposed = preview["proposed_actions"][0]
    assert proposed["evidence_ids"] == [evidence[0]["id"]]
    assert preview["review_required"] is True

    # 影响结果不得自动转成建议：工作区建议数量不变
    response = await client.get(
        f"/api/research-subjects/{subject['id']}/workspace", headers=headers
    )
    assert len(response.json()["action_recommendations"]) == 1

    # 4. 人工把影响结果转为待复核行动建议
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/action-recommendations",
        json={
            "action_type": proposed["action_type"],
            "title": proposed["title"],
            "rationale": proposed["rationale"],
            "risk_level": proposed["risk_level"],
            "evidence_ids": proposed["evidence_ids"],
            "related_claim_ids": preview["affected_claim_ids"],
            "status": "needs_review",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    converted = response.json()
    assert converted["status"] == "needs_review"
    assert converted["evidence_ids"] == [evidence[0]["id"]]
    assert "generated" in _history_actions(converted)

    # 5. 确认：保留前后内容与状态，记录备注和时间
    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/action-recommendations/{converted['id']}",
        json={"status": "confirmed", "review_note": "订单取消属实，同意重新评估"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["reviewed_at"] is not None
    assert confirmed["review_note"] == "订单取消属实，同意重新评估"
    confirm_audit = next(item for item in confirmed["history"] if item["action"] == "confirmed")
    assert confirm_audit["previous_status"] == "needs_review"
    assert confirm_audit["new_status"] == "confirmed"
    assert confirm_audit["previous_content"] == confirm_audit["new_content"]
    assert confirm_audit["review_note"] == "订单取消属实，同意重新评估"
    assert confirm_audit["user_id"] == user["user"]["id"]

    # 6. 驳回：必须填原因；驳回后状态与审计完整
    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/action-recommendations/{converted['id']}",
        json={"status": "rejected"},
        headers=headers,
    )
    assert response.status_code == 400

    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/action-recommendations/{converted['id']}",
        json={"status": "rejected", "review_note": "证据不足以支撑该动作"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    rejected = response.json()
    assert rejected["status"] == "rejected"
    reject_audit = next(item for item in rejected["history"] if item["action"] == "rejected")
    assert reject_audit["previous_status"] == "confirmed"
    assert reject_audit["new_status"] == "rejected"

    # 7. 审计完整性：同一建议的审计按时间串联 generated → confirmed → rejected
    actions = _history_actions(rejected)
    assert actions.count("generated") == 1
    assert "confirmed" in actions and "rejected" in actions

    # 8. 判断的人工复核同样落审计
    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/claims/{cited_claim['id']}",
        json={"status": "confirmed", "review_note": "已核对年报数据"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    claim_history = response.json()["history"]
    assert any(item["action"] == "confirmed" for item in claim_history)
    claim_confirm = next(item for item in claim_history if item["action"] == "confirmed")
    assert claim_confirm["previous_content"] == cited_claim["content"]
    assert claim_confirm["new_content"] == cited_claim["content"]

    # 上传的 PDF 与研究对象绑定关系正确
    assert uploaded_file["research_subject_id"] == subject["id"]


async def test_generate_assets_requires_material(client, monkeypatch):
    """没有可解析材料时生成资产应返回 400。"""
    install_llm_mocks(monkeypatch)
    token = (await register_user(client, "no-material@test.com"))["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/research-subjects",
        json={"company_name": "空壳测试公司"},
        headers=headers,
    )
    subject_id = response.json()["id"]
    response = await client.post(
        f"/api/research-subjects/{subject_id}/generate-assets", headers=headers
    )
    assert response.status_code == 400
    assert "研究材料" in response.json()["detail"]


async def test_generate_assets_llm_failure_maps_to_503(client, monkeypatch):
    """模型服务不可用 → 503；返回非结构化结果 → 502。"""
    token = (await register_user(client, "llm-fail@test.com"))["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/research-subjects",
        json={"company_name": "模型失败测试公司"},
        headers=headers,
    )
    subject_id = response.json()["id"]

    pdf_bytes = (FIXTURES_DIR / "sample.pdf").read_bytes()
    response = await client.post(
        "/api/files",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={"research_subject_id": subject_id},
        headers=headers,
    )
    assert response.status_code == 200

    monkeypatch.setattr("app.services.research_asset_generator.chat", await failing_chat(runtime=True))
    response = await client.post(
        f"/api/research-subjects/{subject_id}/generate-assets", headers=headers
    )
    assert response.status_code == 503

    monkeypatch.setattr("app.services.research_asset_generator.chat", await failing_chat(runtime=False))
    response = await client.post(
        f"/api/research-subjects/{subject_id}/generate-assets", headers=headers
    )
    assert response.status_code == 502


async def test_event_and_preview_validation(client, monkeypatch):
    """事件与影响预览的输入校验：空事件 400；无判断/证据时预览 502。"""
    install_llm_mocks(monkeypatch)
    _, token, headers, subject, _, _ = await setup_subject_with_evidence(
        client, "validation-user@test.com"
    )

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/events",
        json={"title": "   ", "description": "内容存在但标题是空白"},
        headers=headers,
    )
    assert response.status_code == 400

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/events",
        json={"title": "正常事件", "description": "描述"},
        headers=headers,
    )
    assert response.status_code == 200
    event = response.json()

    # 只有证据、没有判断和建议 → analyze_event_impact 仍可执行（证据存在）
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/events/{event['id']}/impact-preview",
        headers=headers,
    )
    assert response.status_code == 200

    # 无判断无证据的全空对象 → 502（结构化分析前置校验）
    token2 = (await register_user(client, "empty-preview@test.com"))["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = await client.post(
        "/api/research-subjects", json={"company_name": "无材料公司"}, headers=headers2
    )
    empty_subject_id = response.json()["id"]
    response = await client.post(
        f"/api/research-subjects/{empty_subject_id}/events",
        json={"title": "事件", "description": "描述"},
        headers=headers2,
    )
    empty_event_id = response.json()["id"]
    response = await client.post(
        f"/api/research-subjects/{empty_subject_id}/events/{empty_event_id}/impact-preview",
        headers=headers2,
    )
    assert response.status_code == 502


async def test_action_recommendation_input_validation(client, monkeypatch):
    """行动建议引用必须属于当前研究对象；复核状态必须合法。"""
    install_llm_mocks(monkeypatch)
    _, token, headers, subject, _, _ = await setup_subject_with_evidence(
        client, "rec-validation@test.com"
    )

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/action-recommendations",
        json={
            "action_type": "site_visit",
            "title": "走访核实",
            "rationale": "依据",
            "evidence_ids": ["不存在的证据ID"],
            "status": "needs_review",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "证据" in response.json()["detail"]

    response = await client.post(
        f"/api/research-subjects/{subject['id']}/action-recommendations",
        json={
            "action_type": "site_visit",
            "title": "走访核实",
            "rationale": "依据",
            "status": "auto_approved",
        },
        headers=headers,
    )
    assert response.status_code == 400


async def test_reject_requires_note_for_claims(client, monkeypatch):
    """判断/假设驳回必须填原因（与行动建议一致）。"""
    install_llm_mocks(monkeypatch)
    _, token, headers, subject, _, _ = await setup_subject_with_evidence(
        client, "claim-reject@test.com"
    )
    response = await client.post(
        f"/api/research-subjects/{subject['id']}/generate-assets", headers=headers
    )
    claim_id = response.json()["claims"][0]["id"]

    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/claims/{claim_id}",
        json={"status": "rejected"},
        headers=headers,
    )
    assert response.status_code == 400

    response = await client.patch(
        f"/api/research-subjects/{subject['id']}/claims/{claim_id}",
        json={"status": "rejected", "review_note": "结论与材料不符"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

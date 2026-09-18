# 弈金企业金融动态尽调 MVP 实施计划

对应设计：[企业金融动态尽调与决策智能体设计](../superpowers/specs/2026-09-18-enterprise-financial-agent-design.md)

目标：在保留现有 PDF 解析、证据引用、人工复核和报告导出的前提下，把产品主流程从“公司研究/报告生成”切换为“企业金融尽调/风险与金融行动建议”。

原则：先完成一个可演示、可评测、可回溯的闭环；不重命名所有现有表和接口，不接真实银行核心系统，不实现自动授信或真实金融操作。

## 实施顺序

### 1. 同步项目上下文

修改：

- `docs/context/current-state.md`
- `docs/context/next-actions.md`
- `docs/context/decision-log.md`

动作：

1. 将产品主定位更新为“企业金融动态尽调与决策智能体”。
2. 把 `ResearchSubject` 明确标记为当前实现中的兼容持久化对象，前端语义改为企业金融对象。
3. 记录不做自动授信、自动支付和真实核心系统接入。
4. 将下一步唯一行动改为“完成企业尽调首个端到端闭环”。

验证：文档中不再同时把“公司研究工作台”和“企业金融尽调智能体”写成两个并列产品中心。

### 2. 增加企业事件与金融行动对象

修改：

- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/api/research_subjects.py`

新增最小对象：

```text
BusinessEvent
  research_subject_id
  user_id / organization_id
  title / description
  source_type / source_reference
  event_time
  status

ActionRecommendation
  research_subject_id
  user_id / organization_id
  action_type
  title / rationale
  risk_level
  evidence_ids
  related_claim_ids / related_assumption_ids
  status: needs_review / confirmed / rejected
  review_note / reviewed_at
```

实现约束：

- 继续使用现有 `ResearchSubject` 外键，避免第一阶段做表和 API 的全量重命名。
- 所有新增查询都校验 `user_id`，并保留 `organization_id` 字段供后续机构隔离使用。
- 行动建议只能被人工确认、驳回或编辑，不能触发授信、支付、调额或外部发送。
- 使用现有 `ResearchAssetAudit` 扩展审计范围，或在确有必要时新增同等不可变审计记录；不复制两套审核逻辑。

API 最小集合：

- `POST /api/research-subjects/{id}/events`
- `GET /api/research-subjects/{id}/events`
- `GET /api/research-subjects/{id}/action-recommendations`
- `PATCH /api/research-subjects/{id}/action-recommendations/{recommendation_id}`

验证：可创建事件、读取同一用户对象下的事件和建议；跨用户访问返回 404；建议审核动作留下审计记录。

### 3. 将生成流程改为企业尽调结构化输出

修改：

- `backend/app/services/research_asset_generator.py`
- `backend/app/services/orchestrator.py`
- `backend/app/agents/registry.py`
- 必要时新增 `backend/app/services/enterprise_due_diligence.py`

动作：

1. 保留现有 `generate-assets` 接口兼容，内部增加企业尽调输出模式。
2. 输入只使用企业对象下已解析的材料和公开检索结果，输出结构化 JSON。
3. 输出至少包含：企业事实、当前经营判断、风险假设、证据缺口、融资需求、行动建议、人工复核事项。
4. 每个关键事实和判断必须带 `evidence_ids` 或明确的 `insufficient` 状态。
5. 只允许已注册的 Agent 名称，禁止 Commander 编造 Agent。
6. 将旧的“报告合成”降为导出步骤，不作为首屏主结果。

推荐的结构化结果：

```json
{
  "enterprise_facts": [],
  "risk_hypotheses": [],
  "financing_needs": [],
  "action_recommendations": [],
  "evidence_gaps": [],
  "review_items": []
}
```

验证：使用固定材料和 mock provider 时，输出能稳定解析；缺少证据时不生成确定性事实；生成结果写入企业对象并关联证据。

### 4. 增加事件影响分析

修改：

- `backend/app/services/enterprise_due_diligence.py`
- `backend/app/api/research_subjects.py`
- `backend/app/schemas/__init__.py`

动作：

1. 用户提交一条企业/行业事件。
2. 系统读取该企业当前已确认或待核验的判断、假设、挑战和行动建议。
3. Agent 只判断事件影响：增强、削弱、不相关或待核验。
4. 写入事件与受影响资产的关联结果。
5. 生成新的人工复核事项，不自动覆盖历史判断。

验证：输入“核心客户订单减少 30%”等固定事件后，系统能指出受影响判断，保留旧版本，并生成新的待复核行动建议。

### 5. 重做企业尽调驾驶舱

修改：

- `frontend/src/app/dashboard/research/page.tsx`
- `frontend/src/app/dashboard/research/[id]/page.tsx`
- `frontend/src/lib/api.ts`
- 必要时修改 `frontend/src/components/Sidebar.tsx`

页面调整：

1. 列表页从“公司研究”改为“企业尽调”，保留旧 URL 兼容。
2. 创建对象时允许输入企业名称、行业和场景，不要求股票代码。
3. 详情页第一屏展示：企业状态、关键风险、融资需求、待处理事件和行动建议。
4. 证据、反方和审计历史继续折叠展示，避免把内部处理过程堆在主界面。
5. 增加“录入新事件”入口和事件影响结果。
6. 将“生成研究报告”改成次级的“导出尽调备忘录”，保留已有格式能力。
7. 每条行动建议提供确认、驳回和编辑入口，并显示人工状态。

验证：桌面和窄屏布局可用；刷新页面后企业状态、事件、建议和复核状态恢复；旧报告列表仍能访问。

### 6. 建立可复现评测和端到端验证

新增或修改：

- `backend/tests/test_enterprise_due_diligence.py`
- `backend/tests/test_research_subject_access.py`
- `backend/tests/fixtures/enterprise_supplier/`
- `test_demo.py`

固定案例：表面优质的汽车零部件供应商，材料包含企业介绍、订单、客户集中度、财务摘要和回款信息；另准备一条“核心客户订单减少 30%”事件。

必须验证：

- PDF 上传、解析和页码引用；
- 企业画像、风险假设和行动建议 schema；
- 引用缺失时显示待核验；
- 事件影响判断；
- 人工确认、驳回、编辑和审计历史；
- 用户隔离；
- 旧的报告导出和演示入口不回归；
- 前端构建通过。

验收命令：

```bash
python -m pytest backend/tests
npm --prefix frontend run build
python test_demo.py
```

若当前环境没有 pytest，先补充开发依赖或改用标准库测试，但不能以“没有测试框架”为理由跳过验证。

## 文件变更边界

本轮实现允许触碰：

- 上述上下文文档；
- 现有研究模型、schema、API、服务和研究页面；
- 新增企业事件、行动建议和测试文件。

本轮不触碰：

- 用户认证和机构权限的整体重构；
- 具体模型 Provider SDK；
- 真实银行核心系统和外部金融数据接口；
- 自动授信、支付、交易或对外发送；
- 与该闭环无关的旧页面和部署配置。

## Definition of Done

当用户可以在一个企业对象内完成“上传材料 → 形成画像 → 识别风险/需求 → 生成行动建议 → 人工确认 → 输入事件 → 更新受影响判断 → 导出可审计尽调备忘录”，并且关键路径测试、权限检查和前端构建均通过时，第一阶段完成。

# Current State

## Project

弈金正在从 A 股研究判断工作台升级为面向银行公司金融、普惠金融和风险管理场景的企业金融动态尽调与决策智能体。

## Current Objective

将产品中心从“生成报告”转向“维护企业金融状态、风险判断、证据、融资需求、金融行动建议和人工复核记录”。

## Current Stage

企业金融尽调 MVP 的设计和实施计划已确认；首个端到端闭环已经完成本地确定性 stub 回放，真实模型回放被开发环境 DeepSeek 凭证阻塞。现有 `ResearchSubject` 作为兼容持久化对象保留，前端语义逐步切换为企业金融对象。

## Source Of Truth

- `AGENTS.md`
- `docs/superpowers/specs/2026-09-12-research-judgment-workbench-design.md`
- `docs/superpowers/specs/2026-09-18-enterprise-financial-agent-design.md`
- `docs/plans/2026-09-18-enterprise-financial-agent-implementation-plan.md`
- `backend/app/models/__init__.py`
- `backend/app/api/research_subjects.py`
- `backend/app/services/research_asset_generator.py`
- `frontend/src/app/dashboard/research/page.tsx`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Important Artifacts

- 新增后端模型：`ResearchSubject`、`ResearchClaim`、`ResearchAssumption`、`ResearchChallenge`、`DecisionMemo`
- 新增后端模型：`BusinessEvent`、`ActionRecommendation`
- 新增后端 API：`/api/research-subjects`
- 新增后端服务：`backend/app/services/research_asset_generator.py`
- 新增前端页面：`/dashboard/research`
- 新增前端页面：`/dashboard/research/[id]`

## Recent Progress

- 公司研究对象可以创建和列表展示。
- 公司研究驾驶舱可以展示当前判断、判断图谱、核心假设、反方挑战、决策备忘录和证据数量。
- PDF 上传可以归档到公司研究对象，页码级证据会关联到该对象。
- 公司研究驾驶舱新增“生成判断资产”入口，可把研究材料转成判断、假设、反方挑战和决策备忘录。
- 新增 `/api/research-subjects/{id}/generate-assets`，生成结果直接写入公司研究对象。
- 判断和假设新增证据 ID 关联与核验状态，可在驾驶舱折叠展开查看对应页码/片段。
- 后端返回 `cited / needs_review / insufficient` 三类核验状态，前端显示为“已引用 / 待核验 / 证据不足”。
- 判断和假设新增人工复核动作：确认、驳回、编辑，并保留复核备注和复核时间。
- 判断和假设新增不可变变更历史：确认、驳回、编辑会记录动作、变更前后内容/状态、备注、操作人和时间，并可在卡片内展开查看。
- 企业金融页面已切换为“尽调闭环”入口：支持 PDF 上传、生成尽调资产、记录企业事件、查看行动建议和人工确认/驳回。
- `generate_research_assets` 已扩展为输出金融行动建议；建议会绑定证据、判断、假设，并自动写入审计历史。
- 行动建议支持 `needs_review / confirmed / rejected` 状态，不会直接触发授信、调额、支付或交易。
- 新增事件影响预览：对企业事件分析受影响判断/建议、证据缺口和新动作；用户可将新动作转为待复核建议，再走确认/驳回和审计流程。

## New Product Direction

- 首个新闭环为“企业金融尽调智能体”：上传企业材料 → 企业画像 → 风险/融资需求 → 金融行动建议 → 人工复核 → 可审计备忘录。
- 后续通过企业/行业事件影响分析，让新信息改变受影响的判断和建议；不自动授信、调额、支付或交易。
- 报告降为尽调备忘录或业务工作包等导出物，不再作为产品首页的唯一结果。

## Validation Status

已验证：宿主 Python 3.13 依赖可用；Colima、PostgreSQL 和 Redis 正常运行；PDF 上传与页码级证据解析；判断、假设和行动建议生成写回；“核心客户订单下降 30%”事件影响预览；待复核动作确认；`generated`/`confirmed` 审计历史；不同用户读取隔离（返回 404）。

待验证：使用真实 DeepSeek 的材料生成质量、引用选择和事件影响判断。真实调用已实际发出并返回 401，原因是当前开发环境 API Key 无效；未修改外部密钥。融资需求对象和影响结果批量回放仍未验证。

已知风险：模型认证异常当前从 `/generate-assets` 暴露为 500，需要在后续 Provider 错误分类工作中决定是否转换为用户可执行的 503 提示；本地测试还出现现有 `passlib`/`bcrypt` 版本兼容警告，但不影响本次认证和权限结果。

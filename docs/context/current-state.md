# Current State

## Project

弈金正在从 A 股研究判断工作台升级为面向银行公司金融、普惠金融和风险管理场景的企业金融动态尽调与决策智能体。

## Current Objective

将产品中心从“生成报告”转向“维护企业金融状态、风险判断、证据、融资需求、金融行动建议和人工复核记录”。

## Current Stage

企业金融尽调 MVP 的设计和实施计划已确认；当前进入首个端到端闭环实现阶段。现有 `ResearchSubject` 作为兼容持久化对象保留，前端语义逐步切换为企业金融对象。

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

## New Product Direction

- 首个新闭环为“企业金融尽调智能体”：上传企业材料 → 企业画像 → 风险/融资需求 → 金融行动建议 → 人工复核 → 可审计备忘录。
- 后续通过企业/行业事件影响分析，让新信息改变受影响的判断和建议；不自动授信、调额、支付或交易。
- 报告降为尽调备忘录或业务工作包等导出物，不再作为产品首页的唯一结果。

## Notes

当前生成入口、证据引用展示、人工复核动作和审计历史已经完成编译、构建和接口级验证；企业金融行动建议和事件影响分析尚未实现。本轮未消耗真实模型调用验证完整材料生成质量。

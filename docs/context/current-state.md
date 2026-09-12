# Current State

## Project

弈金是面向 A 股投研人员的研究判断工作台。

## Current Objective

将产品中心从“生成报告”转向“维护公司研究对象、判断、假设、证据、反方挑战和决策备忘录”。

## Current Stage

第一阶段地基和最小前端驾驶舱已开始落地。

## Source Of Truth

- `AGENTS.md`
- `docs/superpowers/specs/2026-09-12-research-judgment-workbench-design.md`
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

## Notes

当前生成入口、证据引用展示和人工复核动作已经完成编译、构建和接口级验证；本轮未消耗真实模型调用验证完整材料生成质量。

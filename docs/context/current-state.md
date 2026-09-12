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
- `frontend/src/app/dashboard/research/page.tsx`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Important Artifacts

- 新增后端模型：`ResearchSubject`、`ResearchClaim`、`ResearchAssumption`、`ResearchChallenge`、`DecisionMemo`
- 新增后端 API：`/api/research-subjects`
- 新增前端页面：`/dashboard/research`
- 新增前端页面：`/dashboard/research/[id]`

## Recent Progress

- 公司研究对象可以创建和列表展示。
- 公司研究驾驶舱可以展示当前判断、判断图谱、核心假设、反方挑战、决策备忘录和证据数量。
- PDF 上传可以归档到公司研究对象，页码级证据会关联到该对象。

## Notes

当前前端驾驶舱是最小可用版本，尚未接入自动生成判断、假设和挑战。

# Next Actions

## Unique Next Action

将旧 Commander 分析入口并入公司研究对象流程。

## Why This Is Next

公司研究对象已经具备材料、证据、判断、假设、复核和审计历史，但旧的 Commander 分析仍主要围绕 Task/报告输出。下一步要让用户从某个公司研究对象发起分析，并把结果沉淀回该对象的判断资产，而不是形成另一条割裂的报告流。

## Inputs Needed

- `backend/app/api/research_subjects.py`
- `backend/app/api/agents.py`
- `backend/app/agents/*`
- `backend/app/services/research_asset_generator.py`
- `backend/app/models/__init__.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Stop Condition

- 用户可以在公司研究对象页面发起一次结构化分析。
- 分析输入自动包含该研究对象下的材料证据，但前端不刻意展示内部片段注入过程。
- 分析结果写回该研究对象的判断、假设、挑战或备忘录。
- 旧 Task/Commander 输出与新研究对象资产之间保留可追溯关系或明确边界。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

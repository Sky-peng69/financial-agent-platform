# Next Actions

## Unique Next Action

完成企业金融尽调智能体的首个端到端闭环。

## Why This Is Next

现有研究对象已经具备材料、证据、判断、假设、挑战、复核和审计历史，但产品叙事和输出仍主要围绕公司研究报告。下一步要保留现有持久化兼容性，把对象语义切换为企业金融尽调，并新增企业事件、金融需求、行动建议和人工复核闭环。

## Inputs Needed

- `backend/app/api/research_subjects.py`
- `backend/app/api/agents.py`
- `backend/app/agents/*`
- `backend/app/services/research_asset_generator.py`
- `backend/app/models/__init__.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`
- `docs/plans/2026-09-18-enterprise-financial-agent-implementation-plan.md`

## Stop Condition

- 用户可以在企业金融对象页面发起一次结构化尽调。
- 分析输入自动包含该研究对象下的材料证据，但前端不刻意展示内部片段注入过程。
- 分析结果写回风险判断、证据缺口、融资需求和金融行动建议。
- 用户输入新事件后，系统能标记受影响的判断和建议，并要求人工复核。
- 旧 Task/Commander 输出与新研究对象资产之间保留可追溯关系或明确边界。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

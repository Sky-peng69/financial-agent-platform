# Next Actions

## Unique Next Action

把自动分析结果沉淀为公司研究对象下的结构化判断资产。

## Why This Is Next

当前已经有公司研究驾驶舱和手工录入能力，但 AI 分析仍然主要保存在旧 `Task` 报告里。下一步应让模型输出进入 `Claim`、`Assumption`、`Challenge`、`DecisionMemo`，而不是只生成 Markdown。

## Inputs Needed

- `backend/app/services/orchestrator.py`
- `backend/app/api/research_subjects.py`
- `backend/app/models/__init__.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Stop Condition

- 用户可以在某个公司研究对象内触发一次分析。
- 分析完成后至少生成一个判断、一个假设、一个反方挑战和一个备忘录。
- 这些结构化对象能在公司研究驾驶舱中展示。

## Before Continuing Checklist

- [ ] 已读取 current-state.md
- [ ] 已读取 decision-log.md
- [ ] 已读取 next-actions.md
- [ ] 已检查冲突
- [ ] 已确认下一步只做一件事

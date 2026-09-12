# Next Actions

## Unique Next Action

为判断和假设增加版本历史与复核审计记录。

## Why This Is Next

当前判断和假设已经可以被确认、驳回和编辑，但编辑后的内容会覆盖当前文本。下一步要记录“谁在什么时候把什么内容改成了什么、为什么驳回或确认”，否则专业投研场景里无法形成可审计的判断演进链。

## Inputs Needed

- `backend/app/api/research_subjects.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Stop Condition

- 每次确认、驳回和编辑都会写入一条不可变历史记录。
- 历史记录包含资产类型、资产 ID、动作、原内容、新内容、复核备注、操作人和时间。
- 前端可以在判断/假设卡片中展开查看变更历史。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

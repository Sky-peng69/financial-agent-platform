# Next Actions

## Unique Next Action

为判断资产增加人工复核动作：确认、驳回和编辑。

## Why This Is Next

当前判断和假设已经能关联具体证据片段，并在驾驶舱中折叠展示。下一步要让投研人员对这些资产进行复核动作，否则系统只能“生成和展示”，还不能形成真实研究工作流中的判断版本沉淀。

## Inputs Needed

- `backend/app/api/research_subjects.py`
- `backend/app/models/__init__.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Stop Condition

- 用户可以把某条判断或假设标记为“已确认”。
- 用户可以把某条判断或假设标记为“已驳回”并保留原因。
- 用户可以编辑判断或假设文本，保存后仍保留原有证据引用。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

# Next Actions

## Unique Next Action

为自动生成的判断资产补充显式证据引用关系和核验状态。

## Why This Is Next

当前生成入口已经可以把材料分析结果写入 `Claim`、`Assumption`、`Challenge`、`DecisionMemo`。下一步要把每条判断和假设绑定到具体 `DocumentEvidence`，否则用户只能看到结论，不能快速复核“这条判断到底来自哪里”。

## Inputs Needed

- `backend/app/api/research_subjects.py`
- `backend/app/models/__init__.py`
- `backend/app/services/research_asset_generator.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`

## Stop Condition

- 每条自动生成的核心判断至少能关联 1 个 `DocumentEvidence`。
- 驾驶舱可以让用户展开查看对应页码/片段，而不是暴露在主界面里。
- 后端返回资产时包含核验状态：已引用、待核验或证据不足。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

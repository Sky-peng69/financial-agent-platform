# Next Actions

## Unique Next Action

恢复有效的开发环境 DeepSeek 凭证，并重跑真实模型端到端回放；不扩展新 Agent 或新业务域。

## Why This Is Next

企业尽调对象、证据、行动建议和事件影响预览已经落地；本地确定性 stub 已验证“事件 → 影响判断 → 新行动建议 → 人工确认 → 审计记录”和权限隔离。真实 DeepSeek 回放在生成资产时返回 401，下一步只恢复有效开发凭证并验证真实模型输出，不扩展到自动授信或复杂外部系统连接。

## Inputs Needed

- `backend/app/api/research_subjects.py`
- `backend/app/services/research_asset_generator.py`
- `backend/app/models/__init__.py`
- `frontend/src/app/dashboard/research/[id]/page.tsx`
- `docs/plans/2026-09-18-enterprise-financial-agent-implementation-plan.md`

## Stop Condition

- 用户可以在企业金融对象页面发起一次结构化尽调。
- 分析输入自动包含该研究对象下的材料证据，但前端不刻意展示内部片段注入过程。
- 分析结果写回风险判断、证据缺口、融资需求和金融行动建议。
- 用户输入新事件后，系统能基于已有证据标记受影响的判断和建议，并要求人工复核。
- 旧 Task/Commander 输出与新研究对象资产之间保留可追溯关系或明确边界。
- 真实模型调用成功，且结构化资产、引用和事件影响结果通过人工检查。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

## Delivery Rule

在策划、实现和本地验证全部完成前，不执行线上部署；最终只做一次生产部署和线上回归检查。

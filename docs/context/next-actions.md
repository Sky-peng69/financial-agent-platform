# Next Actions

## Unique Next Action

完成 Codex 最终整合验收：确认 Round 1 后端测试、前端构建和剩余风险；不再并行启动第二个 agent。

## Why This Is Next

企业尽调对象、证据、行动建议和事件影响预览已经落地；本地确定性 stub 已验证“事件 → 影响判断 → 新行动建议 → 人工确认 → 审计记录”和权限隔离。Claude Code Round 1 已合并，20 个后端测试双环境通过，前端构建通过。真实 DeepSeek 回放在生成资产时返回 401，待凭证恢复后再单独验证。

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
- Codex 完成最终风险审查，并确认不需要第二个 agent 并行介入。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

## Delivery Rule

在策划、实现和本地验证全部完成前，不执行线上部署；最终只做一次生产部署和线上回归检查。

# Next Actions

## Unique Next Action

扩展多行业固定评测集并完成真实模型质量评估：记录结构化输出、事实与数字、引用覆盖、融资需求和事件影响质量；不并行启动第二个 agent。

## Why This Is Next

企业尽调对象、证据、融资需求、行动建议和事件影响历史回放已经落地；本地确定性 stub 与 1 次真实 DeepSeek 回放已验证“材料 → 资产 → 事件影响 → 持久化 → 人工确认 → 审计记录”和权限隔离。评测格式和首个 pilot 已建立，但当前还缺少多行业样本和人工质量记录。

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
- 用户可在同一企业对象中查看由材料生成的融资需求记录，并保留证据和人工复核状态。
- 事件影响结果可持久化查询，记录受影响资产、证据缺口、建议动作和生成时间；不自动改变既有判断或建议。
- 固定评测集至少覆盖多行业企业和固定问题，记录事实、数字、引用、融资需求、事件影响和人工修改点。

## Before Continuing Checklist

- [x] 已读取 current-state.md
- [x] 已读取 decision-log.md
- [x] 已读取 next-actions.md
- [x] 已检查冲突
- [x] 已确认下一步只做一件事

## Delivery Rule

在策划、实现和本地验证全部完成前，不执行线上部署；最终只做一次生产部署和线上回归检查。

# 弈金：企业金融动态尽调与决策智能体

面向银行公司金融、普惠金融和风险管理场景。产品中心是“企业材料 → 证据 → 企业事实/风险判断 → 金融行动建议 → 经营事件影响分析 → 人工复核 → 审计记录”，而不是旧的上市公司报告生成或 Commander + Specialist 展示。

## ⚡ 新会话启动清单

```bash
# 1. 启动所有容器
docker-compose -f /Users/laurence/Documents/金融agent/docker-compose.yml up -d

# 2. 等 10 秒后端就绪，验证当前企业尽调入口
sleep 10
for path in /dashboard/research /dashboard/tasks; do
  curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:3001${path}"
done

# 3. 如果任何页面 500 → 清 Next.js 缓存
rm -rf /Users/laurence/Documents/金融agent/frontend/.next
docker exec agent-frontend-1 rm -rf /app/.next
docker restart agent-frontend-1
# 等 15 秒重新编译，再跑步骤 2

# 4. 登录 http://localhost:3001/login
# 账号 test@test.com / 123456
```

## ⚠️ 已知不可逆操作

| 操作 | 后果 | 正确做法 |
|------|------|----------|
| 删 `.next` 后不重启容器 | 前端持续 500 | `rm -rf frontend/.next && docker restart agent-frontend-1` |
| 在容器里 `npm install` | 下次重建镜像就丢 | 改 `package.json`→`docker-compose build frontend` |
| volume mount 覆盖了 node_modules | `npm install` 完还是找不到模块 | 删 `.next` + 重启 |

## 参考文档

| 文档 | 路径 | 何时读 |
| ---- | ---- | ------ |
| 新定位设计稿 | [docs/superpowers/specs/2026-09-18-enterprise-financial-agent-design.md](docs/superpowers/specs/2026-09-18-enterprise-financial-agent-design.md) | 产品定位、Agent 架构、MVP 范围、竞赛演示脚本 |
| MVP 实施计划 | [docs/plans/2026-09-18-enterprise-financial-agent-implementation-plan.md](docs/plans/2026-09-18-enterprise-financial-agent-implementation-plan.md) | 实施顺序、验收命令、Definition of Done |
| 项目上下文 | [docs/context/current-state.md](docs/context/current-state.md) / [next-actions.md](docs/context/next-actions.md) / [decision-log.md](docs/context/decision-log.md) | 最新状态、下一步行动、已锁定决策（会话开始先读） |
| 关键架构 | [docs/architecture-financial-agent-platform.md](docs/architecture-financial-agent-platform.md) | 设计架构、新增 Agent、修改编排 |
| 产品 PRD | [docs/PRD-financial-agent-platform.md](docs/PRD-financial-agent-platform.md) | 规划功能、评估优先级 |
| 技术规范 | [docs/specification-financial-agent-platform.md](docs/specification-financial-agent-platform.md) | 写 API、设计 DB、开发 Agent |

## 核心架构

```text
产品中心：企业金融动态尽调与决策智能体（面向银行公司金融/普惠金融/风控场景）

企业尽调闭环:
  上传企业材料 → 页码级证据解析 → AI 结构化尽调（判断/假设/反方/行动建议）
  → 人工确认·驳回·编辑（不可变审计） → 企业事件影响分析 → 尽调备忘录导出

Agent 架构（09-18 设计稿，按金融流程职责划分）:
  事实核验 / 企业画像 / 行业尽调 / 风险与信用 / 金融匹配 / 治理与审计
  旧 Commander + 6 Specialist 保留为既有能力（检索、流式、报告导出），不再作为产品中心
  ResearchSubject 为兼容持久化对象，前端语义已切换为企业金融对象

关键能力:
  · PDF 上传解析 — pypdf 页码级文本抽取，证据定位到"第 N 页"
  · 结构化尽调输出 — 判断/假设/反方/备忘录/行动建议落库并绑定证据
  · 证据核验三态 — cited / needs_review / insufficient，缺证据不编造引用
  · 企业事件影响分析 — 新事件标记受影响判断与建议，生成待复核动作（当前为 preview）
  · 人工复核闭环 — 确认/驳回/编辑 + ResearchAssetAudit 不可变审计历史
  · SSE 流式输出 / DeepSeek 联网搜索 — 旧链路，保留为导出与检索能力

已知缺口（由 Codex 单 agent 按顺序处理，Round 1 后端验证已完成）:
  · FinancingNeed 融资需求对象未落库（目前仅文本）
  · 事件影响结果未持久化（仅 preview，无批量回放）
  · 无真实金融数据源接入（仅用户材料 + 联网搜索）
  · `backend/tests/` 已建立；Round 1 共 20 个测试，宿主 Python 3.13 与容器 Python 3.12 均通过
  · `FinancingNeed` 融资需求对象尚未落库，当前唯一下一项

当前协同状态:
  · Claude Code Round 1 已交付并合并到 main
  · Codex 当前负责最终整合和后续全部实现，不再并行启动第二个 agent
  · Claude Code 不再作为当前阶段的执行依赖
```

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Redis + DeepSeek API
- 前端：Next.js 14 + TypeScript + Tailwind CSS + ReactMarkdown
- 数据库：PostgreSQL 16 + pgvector
- 容器：Docker Compose（开发）/ K8s（生产规划）
- 数据协议：MCP (Model Context Protocol)

## 测试账号

test@test.com / 123456

## 代码原则

1. **先想后写**：不确定时主动问，不隐藏困惑
2. **最小改动**：只改任务相关代码，不碰无关文件和格式
3. **目标驱动**：每个 Task 有判定标准，改完必须验证
4. **匹配风格**：新代码模仿现有代码的命名和结构
5. **读→确认→改→验证**：先读完相关文件确认现状，再动手
6. **基础设施问题不跟功能代码混修**
7. **一次性验证**：写完整的验证脚本，一次跑完所有检查点
8. **实时更新文档**：开发过程中实时更新 CLAUDE.md 和相关文档，让项目文档始终与代码现状同步，保证项目持续完整可交接

## 🧹 已知技术债（勿在功能开发中混着修）

| 问题 | 现象 | 修复方法 |
|------|------|----------|
| Next.js 编译缓存污染 | `.next` 含旧 chunk 引用 → 页面 500 | `rm -rf frontend/.next && docker restart agent-frontend-1` |
| `remark-gfm` 模块解析失败 | 同上根因 | 同上，清 `.next` 即可 |
| volume mount 覆盖 node_modules | 宿主编译产物 ≠ 容器内 | 清 `.next` + 重启，不要反复 `npm install` |

## 必须激活的 Skills

| Skill | 触发场景 |
| ---- | ------ |
| `webapp-testing` | 浏览器验证页面、测试登录/功能是否正常 |
| `frontend-design` | 创建/修改 UI 组件、页面布局、dashboard 重构 |
| `verification-before-completion` | 任何代码改动后验证是否真正生效 |
| `subagent-driven-development` | 多步骤任务可拆解到子 Agent 并行执行 |
| `writing-plans` | 复杂任务需要先出方案再执行 |
| `simplify` | 重构代码、去除冗余、清理逻辑 |

---

## 🏆 工行杯参赛

| 项目 | 详情 |
|------|------|
| 比赛 | 第十七届"工行杯"全国大学生金融科技创新大赛（校赛阶段） |
| 项目名称 | **弈金** — 企业金融动态尽调与决策智能体 |
| 参赛形式 | 个人参赛，全栈独立完成 |

### 参赛文件

| 文件 | 用途 |
|------|------|
| [docs/competition/策划书-弈金.md](docs/competition/策划书-弈金.md) | 校赛策划书主文档（12 章完整版） |
| [docs/competition/需求差距分析.md](docs/competition/需求差距分析.md) | 策划书要求 vs 平台现状对照 |

### 策划书核心叙事

> 弈金让 AI 从"对话框里的聪明人"进化为"可审计的数字金融团队"：上传企业材料 → 形成企业画像 → 识别风险与融资需求 → 生成金融行动建议 → 人工复核 → 新事件驱动判断更新，全程留痕可追溯。

⚠️ 策划书本体（[策划书-弈金.md](docs/competition/策划书-弈金.md)）仍是旧 Commander+Specialist 叙事，待按 09-18 新定位重写（暂缓，先完成企业尽调 MVP 闭环）。

---

## ✅ 已完成：策划书数字金融版导出（09-14）

- **PDF**：`策划书-弈金-数字金融版.pdf`（根目录，6.4MB）✅
- **Word**：`策划书-弈金-数字金融版.docx`（根目录 + docs/competition/ 各一份）✅

生成脚本与模板在 [scripts/](scripts/) 和 [docs/competition/](docs/competition/)（yijin-template.tex、build-digital-pdf.sh）。注意：该版本内容仍是旧叙事，重写策划书后需重新导出。

### 参赛注意事项

- 答辩演示按 09-18 设计稿 §9 八步脚本：汽车零部件供应商案例（表面优质、客户集中 + 现金流风险），重点是"企业变化 → 判断变化 → 金融行动变化"闭环，而非生成长报告
- 策划书中"省赛阶段"标注的功能为真实规划，答辩时可展开讲
- 避免在评委面前打印 PDF——多列表格会截断

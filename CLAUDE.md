# 金融 Agent 平台

多用户金融 AI Agent SaaS 平台。架构融合 **Anthropic Financial Services**（Skills + Connectors + Subagents）与 **阿里云通义点金**（芯—云—模—智），目标让 AI 从"对话框里的聪明人"进化为**能写会算、可审计可追溯的数字员工**。

## 参考文档（任务开始前必读）

| 文档 | 路径 | 何时读 |
| ---- | ---- | ------ |
| 关键架构 | [docs/architecture-financial-agent-platform.md](docs/architecture-financial-agent-platform.md) | 设计架构、新增 Agent、修改编排、连接器、安全合规 |
| 产品 PRD | [docs/PRD-financial-agent-platform.md](docs/PRD-financial-agent-platform.md) | 规划功能、评估优先级、产品决策 |
| 技术规范 | [docs/specification-financial-agent-platform.md](docs/specification-financial-agent-platform.md) | 写 API、设计 DB、开发 Agent/Skill、测试、部署 |

## 当前代码状态

| 组件 | 状态 | 说明 |
| ---- | ---- | ---- |
| 后端 API | ✅ | FastAPI :8001，`/api/auth/*`、`/api/agents/*`、`/api/tasks` |
| Commander 编排 | ✅ 已验证 | `POST /api/agents/analyze` 端到端跑通：Commander 规划 4 子任务 → 3 Specialist 并行 → 生成 2659 字报告 |
| 6 个 Specialist | ✅ | 含 registry.py + agent_runner.py |
| 单 Agent 运行 | ✅ | `POST /api/agents/{name}/run` |
| Dashboard 智能分析 | ✅ 已接入 | `api.ts` 新增 `analyze()`，首页新增 Commander 输入卡片（编译通过） |
| 前端任务详情 | ⚠️ 未解析 JSON | Commander JSON 仍原样显示 |
| 前端错误处理 | ⚠️ 最小状态 | analyze 有基本 loading/error/retry，但 `request()` 未统一超时 |
| PostgreSQL | ✅ | :5433 |
| Redis | ✅ | :6379 |
| Docker | ✅ | 镜像已重建，bcrypt==4.1.3 持久固化 |
| Git | ✅ | commit `6df8d2e` |

## Demo 任务清单（聚焦跑通核心链路）

> Demo 目标：用户输入问题 → Commander 规划 → 多 Specialist 并行 → 展示综合报告。
> 后端编排引擎已就绪，以下全为前端接入工作。

### Demo-Task 1: api.ts 新增 analyze + Dashboard 智能分析入口 🔥

**为什么**：后端 `POST /api/agents/analyze` 已可用，前端缺 `analyze()` 方法和交互入口。

**做什么**：

1. `frontend/src/lib/api.ts` — 新增 `agents.analyze(title, inputData)`，超时 5 分钟
2. `frontend/src/app/dashboard/page.tsx` — Agent 列表上方新增"智能分析"输入卡片
3. 交互流程：输入问题 → 点分析 → loading → 展示 Commander 计划 + 各专家结果 + 综合报告

**判定标准**：输入"分析茅台是否值得投资"→ Commander 分配 Agent → 页面展示报告。

> 📌 调 `Skill:frontend-design` 做 UI

---

### Demo-Task 2: 任务详情页解析 Commander JSON

**为什么**：Commander 任务的 `input_data` 是 JSON（plan + subtask_results），当前原样显示字符串，不可读。

**做什么**：

1. `frontend/src/app/dashboard/tasks/[id]/page.tsx` — 检测 `agent_name === "commander"`，解析 JSON
2. 展示：编排计划（各子任务状态）+ 各 Specialist 结果折叠面板 + 综合报告

**判定标准**：Commander 任务详情页看到各专家分析，而非一串 JSON。

---

### Demo-Task 3: 基础错误处理（超时 + 重试 + 友好提示）

**为什么**：`request()` 无超时，Analyze 可能跑几分钟，失败时前端白屏。

**做什么**：

1. `api.ts` 的 `request()` — 增加 AbortController 超时（默认 30s，analyze 用 300s）
2. 前端结果区 — loading 骨架屏 + 错误卡片 + 重试按钮

**判定标准**：API 失败时前端不白屏，长时间任务不卡死。

> 📌 完成后调 `Skill:verification-before-completion`

---

## 必须激活的 Skills

以下 Skill 在对应场景 **强制调用**，禁止裸写：

| Skill | 触发场景 |
| ---- | ------ |
| `webapp-testing` | 浏览器验证页面、测试登录/功能是否正常 |
| `frontend-design` | 创建/修改 UI 组件、页面布局、dashboard 重构 |
| `verification-before-completion` | 任何代码改动后验证是否真正生效 |
| `subagent-driven-development` | 多步骤任务可拆解到子 Agent 并行执行 |
| `writing-plans` | 复杂任务需要先出方案再执行 |
| `simplify` | 重构代码、去除冗余、清理逻辑 |

## 测试账号

test@test.com / 123456

## 技术栈

- 后端: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Redis + DeepSeek API
- 前端: Next.js 14 + TypeScript + Tailwind CSS
- 数据库: PostgreSQL 16 + pgvector
- 容器: Docker Compose（开发）/ K8s（生产规划）
- 架构: Commander → 12 Specialist Agents → Report Synthesizer
- 数据协议: MCP (Model Context Protocol)

## 代码原则

1. **先想后写**：不确定时主动问，不隐藏困惑
2. **最小改动**：只改任务相关代码，不碰无关文件和格式
3. **目标驱动**：每个 Task 有判定标准，改完必须验证
4. **匹配风格**：新代码模仿现有代码的命名和结构
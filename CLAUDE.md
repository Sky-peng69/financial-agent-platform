# 金融 Agent 平台

多用户金融 AI Agent SaaS 平台。架构融合 **Anthropic Financial Services**（Skills + Connectors + Subagents）与 **阿里云通义点金**（芯—云—模—智），目标让 AI 从"对话框里的聪明人"进化为**能写会算、可审计可追溯的数字员工**。

## 参考文档（任务开始前必读）

| 文档 | 路径 | 何时读 |
| ---- | ---- | ------ |
| 关键架构 | [docs/architecture-financial-agent-platform.md](docs/architecture-financial-agent-platform.md) | 设计架构、新增 Agent、修改编排、连接器、安全合规 |
| 产品 PRD | [docs/PRD-financial-agent-platform.md](docs/PRD-financial-agent-platform.md) | 规划功能、评估优先级、产品决策 |
| 技术规范 | [docs/specification-financial-agent-platform.md](docs/specification-financial-agent-platform.md) | 写 API、设计 DB、开发 Agent/Skill、测试、部署 |

---

## 当前代码状态

| 组件 | 状态 | 说明 |
| ---- | ---- | ---- |
| 后端 API | ✅ | FastAPI :8001，`/api/auth/*`、`/api/agents/*`、`/api/tasks` |
| Commander 编排 | ✅ 已验证 | `POST /api/agents/analyze` 端到端跑通：Commander 规划 4 子任务 → 3 Specialist 并行 → 生成综合报告 |
| 6 个 Specialist | ✅ | `registry.py` + `agent_runner.py`，每个有独立系统提示词 |
| 单 Agent 运行 | ✅ | `POST /api/agents/{name}/run`（同步）+ `/run-stream`（SSE 流式） |
| Dashboard 智能分析 | ✅ 已接入 | `api.ts` 含 `analyze()`，首页 Commander 输入卡片 |
| 全局侧边栏 | ✅ Codex 风格 | `components/Sidebar.tsx` — 可折叠、近期任务列表、导航高亮 |
| Agent placeholder | ✅ 已差异化 | 每个 Agent 页面显示专属输入示例 |
| **SSE 流式输出** | ✅ 已完成 | `POST /api/agents/{name}/run-stream` — 逐字实时流式，支持停止生成，详见 [agent_runner.py](backend/app/services/agent_runner.py#L52) |
| **DeepSeek 原生联网搜索** | ✅ 已启用 | 所有 LLM 调用默认启用 `web_search_options`（`search_context_size: medium`），模型自动判断是否搜索，和 DeepSeek 官网一致。实现见 [llm.py](backend/app/services/llm.py#L57) |
| **系统提示词日期注入** | ✅ | 每次调用自动注入当前日期 `_today_date()`，提示模型注意时间上下文 |
| **结果复制与重新生成** | ✅ | Agent 页面 `[name]/page.tsx`、任务详情 `tasks/[id]/page.tsx`、Dashboard `page.tsx` 均含复制按钮（反馈动画）和重新生成按钮 |
| **流式完成保留结果** | ✅ | Agent 页面不再自动跳转，结果留在当前页，附带操作按钮 |
| PostgreSQL | ✅ | :5433 |
| Redis | ✅ | :6379 |
| Docker | ✅ | 镜像已重建，bcrypt==4.1.3 持久固化 |
| GitHub | ✅ | `truongthimy405-cell/financial-agent-platform`，remote origin 已配置 |

---

## ✅ Demo 任务清单（全部完成）

> Demo 目标：用户输入问题 → Commander 规划 → 多 Specialist 并行 → 展示综合报告。
> 以下 4 个 Demo Task 全部完成，无剩余待办。

### Demo-Task 1: api.ts 新增 analyze + Dashboard 智能分析入口 ✅

见 [frontend/src/lib/api.ts](frontend/src/lib/api.ts#L89) `runStream()`、[frontend/src/lib/api.ts](frontend/src/lib/api.ts#L175) `analyze()`，Dashboard 页 Commander 输入卡片。

### Demo-Task 2: 任务详情页解析 Commander JSON ✅

见 [frontend/src/app/dashboard/tasks/[id]/page.tsx](frontend/src/app/dashboard/tasks/[id]/page.tsx#L82) — 解析 `input_data` JSON，可视化编排计划 + 子任务结果（可折叠）+ 综合报告。

### Demo-Task 3: 基础错误处理 ✅

`request()` 不再设默认 30s 超时；`analyze()` 设 5min；`runStream()` 用 AbortController + SSE error 事件处理；401/403 统一跳转登录页。

### Demo-Task 4: 单 Agent 运行改为 SSE 流式输出 ✅

- 后端：[agent_runner.py](backend/app/services/agent_runner.py#L52) `run_agent_sse()` — 创建 running Task → 流式调用 DeepSeek → 更新 Task → yield done/error
- API：[agents.py](backend/app/api/agents.py#L54) `POST /api/agents/{name}/run-stream` — `StreamingResponse` + SSE
- 前端：[api.ts](frontend/src/lib/api.ts#L89) `runStream()` — ReadableStream + SSE 帧解析 + AbortController
- UI：[page.tsx](frontend/src/app/dashboard/agents/[name]/page.tsx#L206) — 实时流式卡片 + 停止生成按钮

---

## 🔮 值得优先优化的改进项

| 优先级 | 问题 | 说明 |
| ------ | ---- | ---- |
| 🔴 高 | 无真实金融数据接入 | Agent 仅靠联网搜索文字结果，无结构化数据（股价、财报、宏观指标序列）。建议接入 Tushare Pro / 东方财富 API |
| 🔴 高 | 搜索引用未持久化 | DeepSeek 流式返回的 `search_results` 未保存到 Task，详情页看不到引用来源 |
| 🔴 高 | 无 WebSocket 任务进度 | Commander 多 Agent 并行无实时进度推送，用户只能看骨架屏等待 |
| 🟡 中 | 无用户反馈机制 | 结果无"有用/无用"评分，无法收集偏好数据优化调度 |
| 🟡 中 | 任务不可重跑 | 历史任务只能查看，无法基于原参数重新运行 |
| 🟡 中 | 无 Agent 链式调用 | 无法让一个 Agent 输出作为另一个输入（如"先分析行业再据此选股"） |
| 🟡 中 | 移动端适配差 | 未做响应式断点优化 |
| 🟡 中 | 无 PDF/Excel 导出 | 金融报告用户需要下载专业格式文件 |
| 🟢 低 | 无 A/B 测试 | 无法对比不同 prompt/模型参数的效果 |
| 🟢 低 | 日志/监控缺失 | 无请求耗时、Token 消耗、错误率统计 |
| 🟢 低 | 无单元测试 | 后端 0 + 前端 0 |

---

## ✅ Bug 修复（2026-06-23 全部完成）

> 以下 11 个 bug 已全部修复，详见下方各条目。

### 🔴 P0 — 已修复

- [x] **Bug 1: `_today_date()` 冻结在模块导入时** — 修复：将 `SYSTEM_PROMPT` 常量改为 `get_system_prompt()` 函数，每次请求时动态计算日期
- [x] **Bug 2: `_today_date()` 时区错误** — 修复：`datetime.now(BEIJING_TZ)` 其中 `BEIJING_TZ = timezone(timedelta(hours=8))`
- [x] **Bug 3: SSE 客户端断开后 Task 永久卡 RUNNING** — 修复：在 `run_agent_sse()` 中添加 `finally` 块，兜底将 RUNNING 状态 Task 标记为 failed
- [x] **Bug 4: DB 双提交失败无重试** — 修复：抽取 `_commit_with_retry()` 函数，3 次指数退避重试

### 🟡 P1 — 已修复

- [x] **Bug 5: `chat()` 和 `chat_stream()` 是死代码** — 决策：方案 B，所有调用方统一走 `chat()`/`chat_stream()`。`agent_runner.py` 和 `orchestrator.py` 已改为使用这两个函数
- [x] **Bug 6: SYSTEM_PROMPT 从未传给 Specialist Agent** — 修复：`chat()`/`chat_stream()` 接受 `system_prompt` 参数，内部合并全局 `get_system_prompt()` + Specialist 提示词
- [x] **Bug 7: 搜索引用在所有直接 API 调用中被丢弃** — 修复：Bug 5/6 解决后，所有路径统一走 `chat()`，搜索引用提取逻辑自动生效

### 🟠 P2 — 已修复

- [x] **Bug 8: 输出质量标准在 4 个地方重复定义** — 修复：将 `OUTPUT_QUALITY_STANDARDS` 内容移入 `llm.py` 的 `get_system_prompt()` 单一来源；移除 `registry.py` 中的重复定义和 Specialist 提示词中的嵌入；移除 `agent_runner.py` 和 `orchestrator.py` 用户消息中的重复质量规则
- [x] **Bug 9: 用户消息模板重复** — 修复：提取 `USER_MESSAGE_TEMPLATE` 为模块级常量，`run_agent_stream()` 和 `run_agent_sse()` 共用

### 🔵 P3 — 已修复 / 已记录

- [x] **Bug 10: CSS `display:block` 被 `display:table` 覆盖** — 修复：从 `.markdown-content .table-wrapper, .markdown-content table` 选择器组中移除 `table`，仅保留 `.table-wrapper`
- [x] **Bug 11: globals.css 主题全量重写超出任务范围** — 已记录：当前亮色主题即目标样式；后续如需旧主题或 A/B 测试，将主题变量与表格样式拆分到不同文件

---

## 🗺 Demo 后持续打磨路线图

```text
Phase 1: 数据层（1–2 周）
├── 接入 1 个实时金融数据源（Tushare 或 东方财富）
├── 新增 DataConnector Agent（数据获取 Specialist）
└── 关键指标前端可视化（K 线、趋势图）

Phase 2: 体验层（2–3 周）
├── Commander 编排改为 WebSocket 实时进度推送
├── PDF 报告导出（ReportLab / WeasyPrint）
├── 任务历史搜索 + 过滤 + 一键重跑
└── 移动端响应式适配

Phase 3: 智能层（3–4 周）
├── Agent 链式调用（多步推理流水线）
├── 用户反馈收集 + 基于反馈优化 Agent 调度
├── RAG 知识库（公司研报、政策文件向量化检索）
└── 多轮对话记忆（同一任务上下文延续）

Phase 4: 工程化（4–6 周）
├── 后端测试覆盖（pytest + 70%+）
├── 前端 E2E（Playwright）
├── CI/CD（GitHub Actions → 自动测试 + 部署）
├── API 限流 + 使用量统计面板
└── 生产部署（HTTPS + 域名 + 监控告警）
```

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

- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Redis + DeepSeek API（含原生联网搜索 `web_search_options`）
- 前端：Next.js 14 + TypeScript + Tailwind CSS + ReactMarkdown
- 数据库：PostgreSQL 16 + pgvector
- 容器：Docker Compose（开发）/ K8s（生产规划）
- 架构：Commander → 12 Specialist Agents → Report Synthesizer
- 数据协议：MCP (Model Context Protocol)

## 代码原则

1. **先想后写**：不确定时主动问，不隐藏困惑
2. **最小改动**：只改任务相关代码，不碰无关文件和格式
3. **目标驱动**：每个 Task 有判定标准，改完必须验证
4. **匹配风格**：新代码模仿现有代码的命名和结构

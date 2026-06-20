# 金融 Agent 平台

多用户金融 AI Agent SaaS 平台，基于百炼 Multi-Agent 架构。当前状态：后端 6 个 Specialist + Commander 编排引擎可工作，前端基础页面存在但未对接新架构。

---

## 任务清单

### Task 1: 验证登录流程（前端→后端完整链路）

**为什么**：上次 bcrypt 版本不兼容导致登录 500，每次容器重建都会复发。必须验证从前端页面到后端 API 的登录链路完全正常。

**怎么做**：
1. `docker exec agent-backend-1 pip install bcrypt==4.1.3` 确保 bcrypt 正确
2. 浏览器打开 `http://localhost:3001/login`
3. 用 test@test.com / 123456 登录
4. 确认跳转到 `/dashboard`

**判定标准**：
- 登录不报错，页面跳转到 dashboard
- 侧边栏显示用户名 "测试"

---

### Task 2: 前端对接新增的百炼编排端点

**为什么**：后端新增了 `POST /api/agents/analyze`（Commander 自动规划多 Agent），但前端还是老的"选一个 Agent 运行"模式。前端需要新增一个"一键分析"入口，让用户只需输入问题，Commander 自动分配 Agent。

**怎么做**：
1. 在 `frontend/src/lib/api.ts` 新增 `agents.analyze()` 方法
2. 在 dashboard 首页新增"智能分析"卡片/输入框
3. 用户输入问题 → 调 `/api/agents/analyze` → 展示结果
4. Agent 市场页面保留（展示 6 个 Specialist），但每个 Agent 的介绍要更新

**判定标准**：
- 前端输入"分析茅台是否值得投资"→ Commander 自动分配 Agent → 返回综合报告
- 结果页面能看到 output_data

---

### Task 3: 任务历史页面对接百炼结果

**为什么**：百炼编排任务的 `agent_name` 是 "commander"，`input_data` 存了 JSON（plan + subtask_results），当前前端只能显示简单输出。需要让任务历史页能正确展示编排任务的详细结果。

**怎么做**：
1. 检查 `/api/tasks` 能否正确返回 commander 任务的 JSON
2. 前端 tasks 页面增加展开/折叠各 Specialist 分析结果的功能
3. 如果 input_data 是 JSON，解析并展示各专家结论摘要

**判定标准**：
- 任务历史列表能看到 commander 任务
- 点进去能看到各 Specialist 的分析结果（不是原始 JSON）

---

### Task 4: 接口错误处理健壮性

**为什么**：当前 `POST /api/agents/analyze` 没有 timeout 返回给用户的提示，超时或 API 失败时前端可能卡住。

**怎么做**：
1. orchestrator 中捕获的异常/超时要反映到 output_data 中
2. 前端 api.ts 请求超时设置
3. 前端 loading 状态 + 错误提示

**判定标准**：
- 模拟 API Key 失效，前端应显示友好错误而不是白屏
- 长时间运行的任务不阻塞 UI

---

### Task 5: 修复容器重建后依赖丢失问题

**为什么**：bcrypt==4.1.3 和 email-validator 虽然写入了 requirements.txt，但镜像没重建。每次 `docker-compose down && up` 都会丢依赖。

**怎么做**：
1. `docker-compose build backend` 重建镜像
2. 确认重建后 `docker exec agent-backend-1 pip list | grep -E "bcrypt|email"` 显示正确版本
3. 验证重建后登录可用

**判定标准**：
- `docker-compose down && docker-compose up -d` 后无需手动 pip install
- 登录正常工作

---

### Task 6: 初始化 Git 仓库

**为什么**：项目无版本控制，改动不可追溯。

**怎么做**：
```bash
git init
git add -A
git commit -m "feat: 百炼 Multi-Agent 架构 + 12项代码质量修复"
```

**判定标准**：`git log` 有提交记录。

---

## 当前状态

| 组件 | 状态 | 端口 |
|------|------|------|
| 后端 | ✅ 运行中 | :8001 |
| 前端 | ✅ 运行中 | :3001 |
| PostgreSQL | ✅ 运行中 | :5433 |
| Redis | ✅ 运行中 | :6379 |
| 登录 API | ✅ 可注册/登录 | — |
| 单 Agent | ✅ `/agents/{name}/run` | — |
| 百炼编排 | ⬜ 待前端对接 | `/agents/analyze` |
| 前端登录页 | ⬜ 待浏览器验证 | — |
| Git | ⬜ 未初始化 | — |

## 技术栈

- 后端: Python 3.12 + FastAPI + SQLAlchemy + Redis + DeepSeek API
- 前端: Next.js 14 + TypeScript + Tailwind CSS
- 数据库: PostgreSQL 16
- 架构: 百炼 Commander → Specialist(6) → Report Synthesizer

## 测试账号

- 邮箱: test@test.com
- 密码: 123456

# 金融 Agent 平台

多用户金融 AI Agent SaaS 平台。架构融合 **Anthropic Financial Services**（Skills + Connectors + Subagents）与 **阿里云通义点金**（芯—云—模—智），目标让 AI 从"对话框里的聪明人"进化为**能写会算、可审计可追溯的数字员工**。

## ⚡ 新会话启动清单

```bash
# 1. 启动所有容器
docker-compose -f /Users/laurence/Documents/金融agent/docker-compose.yml up -d

# 2. 等 10 秒后端就绪，验证 3 个页面都 200
sleep 10
for path in /dashboard "/dashboard/agents/macro-economy-analyst" "/dashboard/tasks"; do
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
| 关键架构 | [docs/architecture-financial-agent-platform.md](docs/architecture-financial-agent-platform.md) | 设计架构、新增 Agent、修改编排 |
| 产品 PRD | [docs/PRD-financial-agent-platform.md](docs/PRD-financial-agent-platform.md) | 规划功能、评估优先级 |
| 技术规范 | [docs/specification-financial-agent-platform.md](docs/specification-financial-agent-platform.md) | 写 API、设计 DB、开发 Agent |

## 核心架构

```text
用户提问 → Commander 拆解任务 → 多 Specialist 并行分析 → 报告合成师整合输出

当前 6 个 Specialist Agent:
  宏观经济分析师 / 行业研究员 / 基本面分析师 / 消息面分析师 / 财富顾问 / 报告合成师

关键能力:
  · SSE 流式输出 — 实时逐字推送分析结果
  · DeepSeek 原生联网搜索 — 每条结论附来源链接
  · Commander 编排 — 自动识别问题类型，分派 Agent 并行
  · 搜索引用持久化 — Task.search_references 存档，三页面渲染蓝色链接
  · PDF 一键导出 — @media print（已知瑕疵：多列表格截断）

已知缺口（计划中）:
  · 无真实金融数据源接入（仅联网搜索）
  · 无 Agent 链式调用（依赖关系串行）
  · 无用户反馈机制
  · 无单元测试
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
| 项目名称 | **弈金** — 多 Agent 协作金融分析平台 |
| 参赛形式 | 个人参赛，全栈独立完成 |

### 参赛文件

| 文件 | 用途 |
|------|------|
| [docs/competition/策划书-弈金.md](docs/competition/策划书-弈金.md) | 校赛策划书主文档（12 章完整版） |
| [docs/competition/需求差距分析.md](docs/competition/需求差距分析.md) | 策划书要求 vs 平台现状对照 |

### 策划书核心叙事

> 弈金用 Commander + Specialist 多 Agent 架构，让 AI 从"一个聪明人"进化为"一支数字分析团队"。

---

## 🔨 待办：策划书 PDF 导出（当前任务）

源文件：[docs/competition/策划书-弈金.md](docs/competition/策划书-弈金.md)（~11,000 字，14 章含大量表格/代码块/ASCII 架构图）

### 已完成的准备工作

| 步骤 | 状态 |
|------|:--:|
| 项目改名「融智引擎」→「弈金」（策划书 33 处 + CLAUDE.md + 文件重命名）| ✅ |
| 策划书内容优化：痛点重写（分析师的一天故事线）| ✅ |
| 策划书内容优化：竞品深度剖面（ChatGPT/Bloomberg/扣子 × 各半页）| ✅ |
| 策划书内容优化：商业模式量化（TAM/SAM/SOM + 定价表 + ARR 推演）| ✅ |
| 章节编号修复（8.1 市场规模/8.2 定价/8.3 切入策略/8.4 量化价值/8.5 应用价值）| ✅ |

### 用户已确认的风格参数

- **整体风格**：投行研报风（像中金/中信行研报告 — 深蓝主色、衬线标题、强调数据表格）
- **封面**：带几何装饰（Agent 网络节点连线细线图案）
- **配色**：深 Navy #1a2744 + 紫色强调 #6c5ce7 结合（封面+页眉用深 Navy，表格边框和链接用紫色）
- **字体**：PingFang SC（苹方，系统自带，已确认可用 — fc-list 验证通过）

### 可用工具（已验证）

| 工具 | 路径 | 状态 |
|------|------|:--:|
| Pandoc 3.9 | `/opt/homebrew/bin/pandoc` | ✅ |
| XeLaTeX | `/Library/TeX/texbin/xelatex` | ✅ |
| Playwright | Python 可用 | ✅ |
| `markdown` 库 | Python 3.13 | ✅ |
| PingFang SC 字体 | 系统 `/System/Library/...` | ✅ |
| WeasyPrint | ❌ 缺少 `libgobject-2.0` 系统依赖 | 不可用 |

### PDF 生成方案

**推荐路线：Pandoc + XeLaTeX**（理由：LaTeX 学术级排版，中文 + 表格控制力最强，PingFang 字体直接可用）

备选路线：Markdown → HTML + CSS → Playwright → PDF（CSS 控制更灵活，但表格跨页和分页控制不如 LaTeX）

### 具体执行步骤

1. **写 Pandoc LaTeX 模板**（约 200 行）— 定义封面页、页眉页脚、章节标题样式、表格样式、代码块样式、Blockquote 样式
   - 封面：深 Navy 底色 + 白色文字 + 左侧几何线条装饰（Agent 网络节点）
   - 页眉：左侧"弈金 · 工行杯策划书"，右侧章节名
   - 页脚：页码 `— {n} —` 格式
   - 表格：深 Navy 表头白字 + 隔行浅蓝底 + 竖线隐藏
   - 代码块/ASCII 图：暗 slate 背景 + 等宽字体（Menlo/Monaco）
   - Blockquote：左侧 3px 紫色竖线
   - 链接色：紫色 #6c5ce7

2. **处理 ASCII 架构图**（4.2 节、1.2 节、用户流程图等）— 确保等宽字体 + 浅灰背景

3. **处理 ✓ 和 ✗ 符号** — 策划书表格中有 ✅❌🟢🟡 等 emoji/symbol，确认 XeLaTeX 能渲染

4. **生成 PDF**：`pandoc 策划书-弈金.md -o 策划书-弈金.pdf --pdf-engine=xelatex --template=yijin-template.tex`

5. **调试迭代**：渲染 → 检查分页位置、表格完整性、中文字体 → 微调 LaTeX 参数

6. **输出路径**：`docs/competition/策划书-弈金.pdf`

### 已知会被挑战的点

- 多列表格可能超 A4 宽度 → LaTeX 用 `tabularx` 或 `adjustbox` 缩放
- ASCII 架构图可能跨页断裂 → 包在 `samepage` 或 `minipage` 中
- emoji 符号需要字体支持 → 可能需 `Noto Emoji` 或改用文字替代
- 封面几何装饰线用 LaTeX `tikz` 绘制

### 参赛注意事项

- 策划书中"省赛阶段"标注的功能为真实规划，答辩时可展开讲
- 答辩重点演示 Commander 编排流程（实时进度最直观）
- 避免在评委面前打印 PDF——多列表格会截断

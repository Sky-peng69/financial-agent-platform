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
| Dashboard 智能分析 | ✅ 已接入 | `api.ts` 新增 `analyze()`，首页新增 Commander 输入卡片 |
| 全局侧边栏 | ✅ Codex 风格 | `components/Sidebar.tsx` — 可折叠、近期任务列表、导航高亮 |
| Agent placeholder | ✅ 已差异化 | 每个 Agent 页面显示专属输入示例 |
| SSE 流式输出 | ❌ 待实现 | 见 Demo-Task 4 — 单 Agent 运行目前同步等待，需改为流式 |
| 前端超时/Abort | ⚠️ 已移除默认超时 | `request()` 不再设默认 30s（之前导致非 analyze 请求也被 abort） |
| PostgreSQL | ✅ | :5433 |
| Redis | ✅ | :6379 |
| Docker | ✅ | 镜像已重建，bcrypt==4.1.3 持久固化 |
| GitHub | ✅ | `truongthimy405-cell/financial-agent-platform`，remote origin 已配置 |

## Demo 任务清单

> Demo 目标：用户输入问题 → Commander 规划 → 多 Specialist 并行 → 展示综合报告。
> ✅ Demo-Task 1~3 已完成。当前唯一待做任务：

### ~~Demo-Task 1: api.ts 新增 analyze + Dashboard 智能分析入口~~ ✅ 已完成

### ~~Demo-Task 2: 任务详情页解析 Commander JSON~~ ✅ 已完成

### ~~Demo-Task 3: 基础错误处理~~ ✅ 已完成（`request()` 已移除默认 30s 超时，analyze/run 各设独立超时）

---

### Demo-Task 4: 单 Agent 运行改为 SSE 流式输出 🔥

**为什么**：当前 `POST /api/agents/{name}/run` 同步等待 DeepSeek 响应完才返回，用户面对白屏干等几分钟。需要像 DeepSeek Chat 一样实时流式输出，让用户看到 AI 思考进度，同时避免前端超时 abort。

**现有基础（不需要重写）**：
- `backend/app/services/llm.py` — `chat_stream()` 已实现，返回 `AsyncGenerator[str, None]`
- `sse-starlette` 已安装（3.4.4）
- `backend/app/services/agent_runner.py` — `run_agent_stream()` 目前用非流式调用，需改
- `backend/app/models/__init__.py` — Task 模型有 `output_data: Text` 字段

**后端要做的事**：

#### Step 1: 修改 `agent_runner.py` — 新增流式运行函数

在现有 `run_agent_stream()` 下方新增 `run_agent_sse()`：

```python
# backend/app/services/agent_runner.py 新增

import uuid
from datetime import datetime, timezone
from app.models import Task, TaskStatus

async def run_agent_sse(
    agent_name: str,
    title: str,
    user_input: str,
    user_id: str,
    db: AsyncSession,
):
    """
    SSE 流式运行单个 Agent。
    先创建 Task (status=running)，流式产出 chunk，结束后更新 Task 并 yield 最终结果。
    """
    from app.agents.registry import get_specialist_prompt
    from app.services.llm import get_client

    system_prompt = get_specialist_prompt(agent_name) or ""
    client = get_client()

    # 1) 创建 running 状态的 Task
    task = Task(
        id=str(uuid.uuid4()),
        user_id=user_id,
        agent_name=agent_name,
        title=title,
        input_data=user_input,
        status=TaskStatus.RUNNING,
    )
    db.add(task)
    await db.commit()

    # 2) 流式调用 DeepSeek
    stream = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"任务：{title}\n\n用户输入：{user_input}"},
        ],
        temperature=0.3,
        max_tokens=4096,
        stream=True,
    )

    full_output = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_output += delta
            yield {"type": "chunk", "content": delta}

    # 3) 流结束，更新 Task 为 completed
    task.output_data = full_output
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)
    await db.commit()

    # 4) 最后 yield 任务 ID，前端可据此跳转详情页
    yield {"type": "done", "task_id": task.id}
```

#### Step 2: 修改 `backend/app/api/agents.py` — 新增 SSE 端点

在 `run_agent` 下方新增流式端点：

```python
# backend/app/api/agents.py — 在 run_agent 下方新增

from fastapi.responses import StreamingResponse
import json

@router.post("/{name}/run-stream")
async def run_agent_stream_sse(
    name: str,
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式运行单个 Agent"""
    agent = get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' 不存在")

    async def event_stream():
        async for event in run_agent_sse(
            agent_name=name,
            title=data.title,
            user_input=data.input_data or data.title,
            user_id=user.id,
            db=db,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

> 新增导入：`from fastapi.responses import StreamingResponse` 和 `import json`（放文件顶部）
> 新增导入：`from app.services.agent_runner import run_agent_stream, run_agent_sse`

#### Step 3: 不需要改旧端点

旧的 `POST /api/agents/{name}/run` 保留不变。新增 `POST /api/agents/{name}/run-stream`，前端渐进切换。

**前端要做的事**：

#### Step 4: `frontend/src/lib/api.ts` — 新增流式调用方法

```typescript
// 在 agents 对象中新增 runStream 方法
runStream: (
  name: string,
  data: { agent_name: string; title: string; input_data: string },
  onChunk: (text: string) => void,
  onDone: (taskId: string) => void,
  onError: (err: Error) => void,
): AbortController => {
  const controller = new AbortController();
  const t = getToken();

  (async () => {
    try {
      const res = await fetch(`${API_URL}/api/agents/${name}/run-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(t ? { Authorization: `Bearer ${t}` } : {}),
        },
        body: JSON.stringify(data),
        signal: controller.signal,
      });

      if (!res.ok) throw new ApiError(await res.text(), res.status);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 帧（以 \n\n 分隔）
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || ""; // 保留不完整的最后一帧

        for (const part of parts) {
          const line = part.replace(/^data: /, "").trim();
          if (!line) continue;
          try {
            const event = JSON.parse(line);
            if (event.type === "chunk") {
              onChunk(event.content);
            } else if (event.type === "done") {
              onDone(event.task_id);
            }
          } catch { /* 跳过解析失败的帧 */ }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        // 用户主动取消，不报错
        return;
      }
      onError(err);
    }
  })();

  return controller; // 调用方可以 controller.abort() 取消
};
```

> 需要在文件顶部导入 `getToken`（已存在）。

#### Step 5: `frontend/src/app/dashboard/agents/[name]/page.tsx` — 改用流式

修改 `handleRun()` 函数，当前逻辑：

```ts
// 旧逻辑（替换掉）
const task = await agentsApi.run(name, { ... });
setResult(task);
```

改为流式消费：

```ts
const [streaming, setStreaming] = useState(false);
const [streamText, setStreamText] = useState("");
const controllerRef = useRef<AbortController | null>(null);

async function handleRun() {
  if (!title.trim()) { setError("请输入任务标题"); return; }
  setError("");
  setBusy(true);
  setStreaming(true);
  setStreamText("");
  setResult(null);

  const controller = agentsApi.runStream(
    name,
    { agent_name: name, title: title.trim(), input_data: inputData.trim() },
    // onChunk
    (text) => setStreamText((prev) => prev + text),
    // onDone
    (taskId) => {
      setBusy(false);
      setStreaming(false);
      router.push(`/dashboard/tasks/${taskId}`);
    },
    // onError
    (err) => {
      setError(err.message || "运行失败");
      setBusy(false);
      setStreaming(false);
    },
  );
  controllerRef.current = controller;
}
```

在 JSX 的「分析结果」区域上方新增实时流式预览区：

```tsx
{/* 流式输出区（边跑边写） */}
{streaming && (
  <div className="card p-6 mb-8 animate-fade-up">
    <div className="flex items-center gap-2 mb-4">
      <div className="w-3 h-3 rounded-full bg-[#C9A94E] animate-pulse-gold" />
      <span className="text-[#C9A94E] text-sm font-medium">AI 分析中...</span>
      <button
        onClick={() => controllerRef.current?.abort()}
        className="ml-auto text-[#5A6577] text-xs hover:text-[#D95A4A] transition-colors"
      >
        停止生成
      </button>
    </div>
    {streamText ? (
      <div className="markdown-content">
        <ReactMarkdown>{streamText}</ReactMarkdown>
      </div>
    ) : (
      <div className="flex items-center gap-2 text-[#5A6577] text-sm">
        <span className="w-4 h-4 border-2 border-[#5A6577]/30 border-t-[#C9A94E] rounded-full animate-spin" />
        正在连接 AI...
      </div>
    )}
  </div>
)}
```

> 新增 import：`useRef`（从 react）
> 按钮改文字：busy 时显示"AI 分析中..."而非原来的"AI 分析中..."

**判定标准**：
1. 进入任意 Agent 页面，输入标题，点「开始分析」
2. 出现「AI 分析中...」卡片，**逐字/逐段实时输出 Markdown**
3. 流式结束后自动跳转到任务详情页
4. 点击「停止生成」能中止请求

> 📌 前后端都改完后调 `Skill:verification-before-completion` 验证

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
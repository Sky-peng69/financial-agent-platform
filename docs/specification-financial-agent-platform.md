# 金融 AI Agent 平台 — 需求规范文档

> 参考：Anthropic Financial Services Agent Templates + 阿里云通义点金平台
>
> 版本：v1.0 | 日期：2026-06-20 | 状态：Draft

---

## 目录

1. [系统概述](#1-系统概述)
2. [API 规范](#2-api-规范)
3. [数据模型](#3-数据模型)
4. [Agent 规范](#4-agent-规范)
5. [Skill 开发规范](#5-skill-开发规范)
6. [MCP Connector 规范](#6-mcp-connector-规范)
7. [安全规范](#7-安全规范)
8. [前端交互规范](#8-前端交互规范)
9. [测试规范](#9-测试规范)
10. [运维规范](#10-运维规范)

---

## 1. 系统概述

### 1.1 系统边界

```
┌─────────────────────────────────────────────────────────┐
│                    金融 AI Agent 平台                     │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ 前端 Web  │   │ REST API │   │  MCP     │            │
│  │ (Next.js) │   │ Gateway  │   │ Endpoint │            │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘            │
│       │              │              │                    │
│       └──────────────┼──────────────┘                    │
│                      │                                   │
│  ┌───────────────────▼──────────────────────────────┐   │
│  │              后端服务 (FastAPI)                    │   │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │   │
│  │  │ Auth    │ │ Agent  │ │ Task   │ │ Config  │  │   │
│  │  │ Service │ │ Service│ │ Service│ │ Service │  │   │
│  │  └─────────┘ └───┬────┘ └────────┘ └─────────┘  │   │
│  │                  │                                 │   │
│  │  ┌───────────────▼────────────────────────────┐   │   │
│  │  │          编排引擎 (Orchestrator)             │   │   │
│  │  │  Commander → Harness → Specialist Pool      │   │   │
│  │  └───────────────────┬────────────────────────┘   │   │
│  └──────────────────────┼────────────────────────────┘   │
│                         │                                 │
│         ┌───────────────┼───────────────┐                │
│         ▼               ▼               ▼                │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐         │
│  │PostgreSQL│   │  Redis   │   │ LLM Provider │         │
│  │  (主库)  │   │ (缓存/Q) │   │ (DeepSeek/   │         │
│  │          │   │          │   │  Qwen/Claude)│         │
│  └──────────┘   └──────────┘   └──────────────┘         │
│                                                         │
│  外部系统:                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 行情数据  │ │ 财务数据  │ │ 新闻资讯  │ │ 合规数据  │   │
│  │ (MCP)    │ │ (MCP)    │ │ (MCP)    │ │ (MCP)    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术约束

| 项目 | 约束 |
|------|------|
| 编程语言 | Python 3.12+ (后端), TypeScript 5.x (前端) |
| 框架 | FastAPI 0.110+, Next.js 14+ |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存 | Redis 7 |
| LLM | DeepSeek API (默认), 支持切换 Qwen/Claude |
| 容器化 | Docker + Docker Compose (开发), Kubernetes (生产) |
| 协议 | REST (JSON), MCP (JSON-RPC), WebSocket (实时) |

---

## 2. API 规范

### 2.1 通用规范

```
Base URL: https://api.finagent.com/v1

请求头:
  Authorization: Bearer <jwt_token>
  Content-Type: application/json
  X-Request-ID: <uuid>          # 请求追踪

响应格式:
{
  "code": 0,                    # 0=成功, 非0=错误
  "message": "success",
  "data": { ... },              # 业务数据
  "request_id": "uuid"          # 请求追踪
}

错误格式:
{
  "code": 40001,
  "message": "Invalid input: stock_code is required",
  "detail": { ... },
  "request_id": "uuid"
}

错误码规范:
  0       - 成功
  40001   - 参数校验失败
  40100   - 未认证
  40101   - Token 过期
  40300   - 无权限
  40400   - 资源不存在
  42900   - 请求过于频繁
  50000   - 服务器内部错误
  50001   - LLM 调用失败
  50002   - 数据源不可用
  50400   - 上游超时
```

### 2.2 认证接口

```
POST /v1/auth/register
  请求: { "email": "user@example.com", "password": "******", "name": "用户名" }
  响应: { "user": { "id", "email", "name" }, "token": "jwt..." }
  校验: email 格式, password ≥ 8位含数字+字母

POST /v1/auth/login
  请求: { "email": "user@example.com", "password": "******" }
  响应: { "user": { "id", "email", "name" }, "token": "jwt..." }

POST /v1/auth/refresh
  请求头: Authorization: Bearer <refresh_token>
  响应: { "token": "new_jwt..." }
  说明: access_token 有效期 1h, refresh_token 有效期 7d
```

### 2.3 Agent 接口

```
GET /v1/agents
  描述: 获取可用 Agent 列表
  响应: {
    "agents": [
      {
        "name": "investment-researcher",
        "display_name": "投资研究员",
        "description": "行业研究与公司深度分析",
        "category": "research",
        "capabilities": ["行业分析", "竞争格局", "公司尽调", "ESG评估"],
        "status": "active"
      },
      ...
    ]
  }

GET /v1/agents/{name}
  描述: 获取单个 Agent 详情
  响应: {
    "name": "investment-researcher",
    "display_name": "投资研究员",
    "description": "...",
    "skills": [...],
    "required_connectors": [...],
    "input_schema": { ... },
    "output_schema": { ... }
  }

POST /v1/agents/{name}/run
  描述: 运行单个 Agent（直接调用，不经过 Commander）
  请求: {
    "input": "分析贵州茅台(600519)的财务表现",
    "params": { "stock_code": "600519", "period": "5Y" },
    "options": { "stream": false }
  }
  响应: {
    "task_id": "task_xxx",
    "status": "completed",
    "output": { ... },
    "tokens_used": 15000,
    "elapsed_ms": 28400
  }

POST /v1/agents/analyze
  描述: Commander 编排入口（推荐使用）
  请求: {
    "query": "分析茅台是否值得投资，考虑基本面、行业和风险",
    "options": {
      "agents": ["investment-researcher", "financial-modeler", "risk-controller"],
      "stream": true,
      "timeout": 300
    }
  }
  响应 (非流式): {
    "task_id": "task_xxx",
    "plan": {
      "subtasks": [
        { "id": 1, "agent": "investment-researcher", "description": "..." },
        { "id": 2, "agent": "financial-modeler", "description": "..." }
      ]
    },
    "results": [
      {
        "subtask_id": 1,
        "agent": "investment-researcher",
        "status": "completed",
        "output": { ... },
        "tokens_used": 25000
      },
      ...
    ],
    "synthesis": { ... },
    "tokens_used": 80000,
    "elapsed_ms": 120000
  }
  响应 (SSE 流式):
    event: plan
    data: {"subtasks": [...]}

    event: subtask_start
    data: {"subtask_id": 1, "agent": "investment-researcher"}

    event: subtask_progress
    data: {"subtask_id": 1, "message": "正在获取财务数据..."}

    event: subtask_complete
    data: {"subtask_id": 1, "output": {...}}

    event: synthesis
    data: {"content": "..."}

    event: complete
    data: {"task_id": "task_xxx", "tokens_used": 80000}
```

### 2.4 任务接口

```
GET /v1/tasks
  描述: 获取用户任务列表
  参数: ?page=1&size=20&status=completed&agent=investment-researcher
  响应: {
    "items": [
      {
        "id": "task_xxx",
        "type": "commander",         # commander | single_agent
        "query": "分析茅台...",
        "status": "completed",        # pending | running | completed | failed
        "agent_name": "commander",
        "tokens_used": 80000,
        "created_at": "2026-06-20T10:30:00Z",
        "completed_at": "2026-06-20T10:32:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "size": 20
  }

GET /v1/tasks/{id}
  描述: 获取任务详情（含完整结果）
  响应: {
    "id": "task_xxx",
    "type": "commander",
    "query": "分析茅台是否值得投资...",
    "status": "completed",
    "plan": [ ... ],
    "input_data": {
      "plan": [...],
      "subtask_results": [...]
    },
    "output_data": {
      "synthesis": "...",
      "report": "..."
    },
    "tokens_used": 80000,
    "elapsed_ms": 120000,
    "error": null
  }

POST /v1/tasks/{id}/retry
  描述: 重新执行任务

DELETE /v1/tasks/{id}
  描述: 删除任务记录
```

### 2.5 MCP 管理接口

```
GET /v1/connectors
  描述: 列出已配置的数据连接器
  响应: {
    "connectors": [
      {
        "id": "mcp-market-data",
        "name": "A股行情数据",
        "type": "mcp",
        "status": "connected",
        "last_health_check": "2026-06-20T10:00:00Z"
      }
    ]
  }

POST /v1/connectors/test
  描述: 测试连接器可用性
  请求: { "connector_id": "mcp-market-data" }
  响应: { "status": "healthy", "latency_ms": 45 }
```

---

## 3. 数据模型

### 3.1 核心实体

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    role VARCHAR(20) DEFAULT 'user',  -- admin, user, readonly
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 租户表 (多租户隔离)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',  -- free, pro, team, enterprise
    quota_daily INTEGER DEFAULT 100,
    quota_used_today INTEGER DEFAULT 0,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent 配置表
CREATE TABLE agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),          -- research, trading, risk, compliance, ...
    system_prompt TEXT NOT NULL,
    skills TEXT[] DEFAULT '{}',     -- 引用的 Skill 名称数组
    connectors TEXT[] DEFAULT '{}', -- 需要的连接器
    model VARCHAR(50) DEFAULT 'deepseek-chat',
    max_tokens INTEGER DEFAULT 8000,
    temperature FLOAT DEFAULT 0.1,
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 任务表
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    type VARCHAR(20) NOT NULL,       -- commander, single_agent
    query TEXT NOT NULL,
    agent_name VARCHAR(100),         -- commander 或具体 agent
    status VARCHAR(20) DEFAULT 'pending',
    input_data JSONB,                -- 编排计划 + 子任务结果
    output_data JSONB,               -- 最终输出
    tokens_used INTEGER DEFAULT 0,
    elapsed_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 子任务表 (编排任务的子任务)
CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) NOT NULL,
    seq INTEGER NOT NULL,            -- 子任务序号
    agent_name VARCHAR(100) NOT NULL,
    description TEXT,
    input JSONB,
    output JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    tokens_used INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 审计日志表
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    action VARCHAR(100) NOT NULL,    -- agent.call, task.create, connector.access
    resource_type VARCHAR(50),       -- agent, task, connector
    resource_id VARCHAR(100),
    detail JSONB,                    -- 操作详情
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 数据连接器配置表
CREATE TABLE connector_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) DEFAULT 'mcp',  -- mcp, rest, websocket
    config JSONB NOT NULL,           -- 连接配置 (URL, 凭证引用等)
    status VARCHAR(20) DEFAULT 'inactive',
    last_health_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Skill 表
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    category VARCHAR(50),
    version INTEGER DEFAULT 1,
    content TEXT NOT NULL,           -- Markdown 格式的技能定义
    is_public BOOLEAN DEFAULT false,
    tenant_id UUID REFERENCES tenants(id),  -- NULL = 系统内置
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Redis 数据结构

```
# 会话缓存
session:{session_id} → JSON { user_id, tenant_id, expires_at }

# 任务进度 (实时推送)
task:{task_id}:progress → JSON { status, subtasks_completed, total_subtasks }

# 速率限制
ratelimit:{tenant_id}:{date} → INTEGER (当天已用次数)

# Agent 执行状态
agent:{agent_name}:status → "idle" | "busy"
agent:{agent_name}:queue → LIST of task_ids

# 数据缓存
cache:{connector}:{cache_key} → JSON (5min TTL)
```

---

## 4. Agent 规范

### 4.1 Agent 定义文件格式

每个 Agent 在 `agents/{name}/AGENT.md` 中定义：

```markdown
# Agent: Investment Researcher (投资研究员)

## 元数据
- **名称**: investment-researcher
- **类别**: research
- **模型**: deepseek-chat
- **温度**: 0.1
- **最大 Token**: 8000

## 角色定义
你是一位资深金融研究员，拥有 15 年买方研究经验。
你擅长行业分析、公司深度研究和竞争格局分析。
你的分析风格严谨、数据驱动，所有结论必须有数据支撑。

## 能力边界
**你能做**:
- 行业分析与趋势判断
- 公司商业模式和护城河分析
- 竞争格局和市场份额研究
- ESG 评估
- 投资论点构建

**你不能做**:
- 给出买卖建议
- 设定目标价格
- 做出投资决策

## 所需数据源
- 财务数据 (财务报表、财务比率)
- 行业数据 (市场规模、增长率、集中度)
- 新闻资讯 (公司公告、行业新闻)
- 研报数据 (券商研报)

## 输出规范
输出格式为结构化 Markdown，包含:
1. 执行摘要 (不超过 200 字)
2. 行业分析 (行业概况、增长动力、风险)
3. 公司分析 (商业模式、竞争优势、财务表现)
4. 竞争格局 (主要竞争对手、市场份额、差异化)
5. 风险因素 (行业风险、公司风险、宏观风险)
6. 投资观点 (看多/看空理由，不含建议)

每个部分必须引用具体数据来源。

## 质量检查
- [ ] 所有数据标注来源和日期
- [ ] 结论有数据支撑
- [ ] 无投资建议性语言
- [ ] 无明显事实错误

## 行为约束
- 永远不输出投资建议 ("买入"/"卖出"/"持有")
- 不确定时明确说"数据不足以判断"
- 使用中文输出 (专业术语可保留英文)
```

### 4.2 Commander Agent 规范

Commander 是特殊的编排 Agent，其系统提示词需包含:

```
## 编排规则
1. **任务理解**: 从用户输入中提取: 标的、分析角度、时间范围、输出格式
2. **Agent 选择**:
   - 涉及行业/公司分析 → investment-researcher
   - 涉及估值/模型 → financial-modeler
   - 涉及风险 → risk-controller
   - 涉及合规 → compliance-officer
   - 涉及市场数据 → market-monitor
3. **并行 vs 串行**: 无依赖的子任务并行执行，有依赖的串行
4. **冲突消解**: 当 Agent 结论冲突时，标注冲突点并请求用户决策
5. **报告合成**: 汇总各 Agent 输出，生成连贯的综合报告

## 输出格式
{
  "plan": [
    { "seq": 1, "agent": "agent-name", "description": "...", "depends_on": [] },
    ...
  ],
  "reasoning": "选择这些 Agent 的理由"
}
```

### 4.3 Agent 间通信协议

```
Handoff 协议 (Agent → Agent):
{
  "from": "commander",
  "to": "investment-researcher",
  "type": "task_assignment",
  "payload": {
    "task_id": "task_xxx",
    "subtask_id": 1,
    "instruction": "分析贵州茅台的白酒行业地位和竞争格局",
    "context": { ... },          // 上游 Agent 的关键发现
    "deadline": "2026-06-20T10:35:00Z"
  }
}

Agent → Commander 响应:
{
  "from": "investment-researcher",
  "to": "commander",
  "type": "task_result",
  "payload": {
    "task_id": "task_xxx",
    "subtask_id": 1,
    "status": "completed",
    "output": { ... },
    "confidence": 0.85,          // Agent 对结果的信心度
    "caveats": ["数据截至 2026Q1", "未考虑政策变化影响"]
  }
}
```

---

## 5. Skill 开发规范

### 5.1 Skill 文件结构

遵循 Anthropic 的 Skill 设计模式：

```
skills/
├── core/                       # 系统内置核心技能
│   ├── financial-analysis/     # 财务分析技能包
│   │   ├── SKILL.md            #   主技能定义
│   │   ├── ratio-analysis.md   #   比率分析
│   │   ├── dupont-analysis.md  #   杜邦分析
│   │   └── cashflow.md         #   现金流分析
│   ├── valuation/              # 估值技能包
│   │   ├── SKILL.md
│   │   ├── dcf-model.md
│   │   ├── comps-analysis.md
│   │   └── lbo-model.md
│   ├── data-processing/        # 数据处理
│   └── document-generation/    # 文档生成
│
├── domain/                     # 领域专业技��
│   ├── equity-research/
│   ├── investment-banking/
│   ├── wealth-management/
│   ├── risk-management/
│   ├── insurance/
│   └── compliance/
│
└── custom/                     # 用户自定义技能
    └── {tenant_id}/
```

### 5.2 Skill 定义规范模板

```markdown
---
name: dcf-model
display_name: DCF 估值模型
category: valuation
version: 1.0.0
author: system
requires:
  connectors: [financial-data, market-data]
  skills: [ratio-analysis]
inputs:
  ticker:
    type: string
    description: 股票代码
  period:
    type: string
    enum: [3Y, 5Y, 10Y]
    default: 5Y
output:
  format: json
  schema: dcf-output.schema.json
---

# DCF 估值模型

## 概述
基于自由现金流折现法 (DCF) 对公司进行估值。

## 前置条件
- 需要最近 5 年的财务报表数据
- 需要当前无风险利率和市场风险溢价

## 执行步骤

### Step 1: 获取历史财务数据
通过 financial-data 连接器获取目标公司过去 5 年的:
- 收入、EBIT、D&A、CapEx、营运资本变动
- 计算历史 FCF = EBIT*(1-t) + D&A - CapEx - ΔWC

### Step 2: 预测未来现金流
基于历史增长率 + 行业趋势，预测未来 5 年 FCF:
- 收入增长率: 历史 CAGR + 行业调整
- 利润率: 历史平均 ± 趋势调整
- 终端增长率: 默认 2.5% (中国 GDP 长期增长率)

### Step 3: 计算 WACC
- 无风险利率: 当前 10 年期国债收益率
- 股权风险溢价: 5.5% (中国市场默认值)
- Beta: 从市场数据获取
- 债务成本: 公司最新发债利率或行业平均
- WACC = (E/V)*Ke + (D/V)*Kd*(1-t)

### Step 4: DCF 计算
- PV of projected FCFs = Σ(FCF_t / (1+WACC)^t)
- Terminal Value = FCF_5*(1+g) / (WACC-g)
- Enterprise Value = PV + PV of TV
- Equity Value = EV - Net Debt
- 每股价值 = Equity Value / Shares Outstanding

### Step 5: 敏感性分析
对 WACC (±1%) 和 终端增长率 (±0.5%) 做敏感性分析

## 输出格式
```json
{
  "ticker": "600519",
  "valuation_date": "2026-06-20",
  "wacc": 0.085,
  "terminal_growth": 0.025,
  "enterprise_value": 2.5e12,
  "equity_value": 2.3e12,
  "per_share_value": 1830.5,
  "sensitivity": {
    "wacc_range": [0.075, 0.085, 0.095],
    "growth_range": [0.02, 0.025, 0.03],
    "matrix": [[...], [...], [...]]
  },
  "key_assumptions": {
    "revenue_growth": 0.12,
    "ebit_margin": 0.65,
    "capex_pct": 0.03
  }
}
```

## 验证规则
- WACC 应在 6%-15% 范围内
- 终端增长率应 ≤ 长期 GDP 增长率
- 每股价值应为正数
- 所有输入数据需标注来源日期

## 异常处理
- 如果公司 FCF 为负: 使用收入倍数法作为替代
- 如果无法获取 Beta: 使用行业平均 Beta
- 如果 WACC < 增长率: 标记警告，使用保守假设
```

### 5.3 Skill 生命周期管理

```
创建 → 测试 → 发布 → 版本管理 → 废弃

规则:
1. 新增技能不改变已有技能的版本号
2. 修改技能行为 → 增加主版本号 (1.x → 2.0)
3. 修改技能描述/示例 → 增加次版本号 (1.0 → 1.1)
4. 废弃技能在 SKILL.md 头部标记 deprecated: true
5. Agent 可锁定依赖的 Skill 版本
```

---

## 6. MCP Connector 规范

### 6.1 连接器配置格式

```json
// .mcp.json (位于 agent 目录或全局配置)
{
  "mcpServers": {
    "market-data-a": {
      "type": "streamableHttp",
      "url": "https://mcp.market-data.cn/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_MARKET_DATA_TOKEN}"
      },
      "timeout": 10000,
      "retry": {
        "max_attempts": 3,
        "backoff_ms": 1000
      },
      "rateLimit": {
        "maxRequestsPerMinute": 60
      }
    },
    "financial-reports": {
      "type": "streamableHttp",
      "url": "https://mcp.financial-data.cn/mcp",
      "headers": {
        "X-API-Key": "${MCP_FINANCIAL_KEY}"
      },
      "timeout": 15000
    },
    "internal-documents": {
      "type": "streamableHttp",
      "url": "https://mcp.internal.company.com/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_INTERNAL_TOKEN}"
      },
      "transport": {
        "proxy": "http://proxy.internal.com:8080"
      }
    }
  }
}
```

### 6.2 连接器开发规范

新增 MCP 连接器需满足:

| 要求 | 说明 |
|------|------|
| **标准协议** | 实现 MCP Specification (JSON-RPC 2.0) |
| **认证** | 支持 API Key / Bearer Token / OAuth 2.0 |
| **错误处理** | 返回标准 MCP 错误码 |
| **速率限制** | 在配置中声明 QPM/QPS 上限 |
| **超时** | 默认 10s，单次调用上限 30s |
| **日志** | 记录每次调用的请求/响应元数据 |
| **健康检查** | 实现 `ping` 方法，定期探测可用性 |
| **版本** | URL 中包含版本号或通过 Header 传递 |

### 6.3 连接器安全要求

```
1. 凭证不落地: 全部通过环境变量引用 ${ENV_VAR}
2. 网络隔离: 生产环境仅允许 Agent 沙箱访问外部 MCP 端点
3. 传输加密: 所有 MCP 通信使用 TLS 1.3
4. 数据最小化: Agent 仅获取任务所需的字段
5. 审计: 每次 MCP 调用记录在 audit_logs 表
```

---

## 7. 安全规范

### 7.1 身份认证

- **JWT Token**: RS256 签名，有效期 1 小时
- **Refresh Token**: 有效期 7 天，单次使用后失效
- **密码**: bcrypt (work factor ≥ 12) 哈希存储
- **MFA**: V2.0 支持 TOTP / 短信验证

### 7.2 授权控制

```
权限模型: RBAC (Role-Based Access Control)

角色定义:
  super_admin:    全部权限 (系统管理)
  tenant_admin:   租户内全部权限 (用户管理、配置、查看所有任务)
  analyst:        创建任务、查看自己的任务、管理 Agent
  readonly:       仅查看 (适合审计/合规角色)

资源级权限:
  - 用户只能查看/操作自己创建的任务
  - tenant_admin 可查看租户内所有任务
  - Agent 配置修改仅限 tenant_admin
  - 连接器配置修改仅限 tenant_admin
```

### 7.3 数据安全

| 维度 | 措施 |
|------|------|
| **传输安全** | TLS 1.3, HSTS, 证书固定 |
| **存储安全** | PostgreSQL TDE, Redis AUTH + TLS |
| **密钥管理** | 环境变量注入, 不写入代码/配置文件/日志 |
| **数据脱敏** | PII/账号字段自动脱敏入日志 |
| **数据隔离** | 租户级 schema 或 row-level security |
| **备份加密** | 备份文件 AES-256 加密 |

### 7.4 输入安全

```
防护措施:
  1. 参数校验: Pydantic v2 严格校验所有输入
  2. SQL 注入: ORM 参数化查询，禁止拼接 SQL
  3. XSS: 前端输出转义 + CSP Header
  4. CSRF: SameSite Cookie + CSRF Token
  5. 速率限制: 按用户/租户/IP 限流
  6. 输入长度限制: query ≤ 5000 字符, 文件名 ≤ 255 字符
  7. 文件上传: 类型白名单 + 病毒扫描 + 大小限制 10MB
```

### 7.5 审计要求

```sql
-- 审计日志必记字段
{
  "event": "agent.call",           // 事件类型
  "timestamp": "2026-06-20T10:30:00.000Z",
  "user": { "id": "uuid", "email": "user@example.com" },
  "tenant": { "id": "uuid", "name": "某券商" },
  "resource": { "type": "agent", "id": "investment-researcher" },
  "action": "run",
  "request": { "input": "...", "params": {...} },
  "response": { "status": "completed", "tokens_used": 25000 },
  "context": {
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "request_id": "req_xxx"
  }
}
```

---

## 8. 前端交互规范

### 8.1 页面结构

```
/login              → 登录页
/register           → 注册页
/dashboard          → 首页 (智能分析入口 + 最近任务)
/dashboard/agents   → Agent 市场 (展示所有可用 Agent)
/dashboard/agents/[name] → Agent 详情 + 直接运行
/dashboard/tasks    → 任务历史列表
/dashboard/tasks/[id] → 任务详情 (含编排过程展示)
/dashboard/settings → 用户设置
/admin              → 管理后台 (tenant_admin)
```

### 8.2 智能分析交互流程

```
1. 用户在首页输入框输入问题
2. 点击"智能分析"或按 Enter
3. 前端 POST /v1/agents/analyze (stream=true)
4. 显示编排计划 (Commander 规划的各子任务)
5. 各子任务并行执行时实时显示进度
6. 全部完成后展示综合报告
7. 用户可导出或分享报告

UI 状态:
  idle → loading (显示 Commander 规划中...) →
  planning (显示任务拆解结果) →
  executing (各 Agent 进度条) →
  synthesizing (整合中...) →
  completed (展示结果)
```

### 8.3 任务详情展示

```
┌─────────────────────────────────────────────┐
│  任务: 分析茅台是否值得投资                   │
│  状态: ✅ 已完成 | 耗时: 2分30秒              │
├─────────────────────────────────────────────┤
│  编排计划                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ 1.行业分析│  │ 2.财务分析│  │ 3.估值模型 │  │
│  │ ✅ 完成   │  │ ✅ 完成   │  │ 🔄 执行中  │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│  ┌──────────┐                                │
│  │ 4.风险评估│                                │
│  │ ⏳ 等待中 │                                │
│  └──────────┘                                │
├─────────────────────────────────────────────┤
│  分析结果                                     │
│  ▶ 行业分析 (点击展开)                        │
│    ┌─────────────────────────────────────┐   │
│    │ 白酒行业 2026 年市场规模...           │   │
│    │ 茅台市占率 18.5%，高端酒细分第一...   │   │
│    └─────────────────────────────────────┘   │
│  ▶ 财务分析 (点击展开)                        │
│  ▶ 估值模型 (点击展开)                        │
│  ▶ 综合报告                                   │
├─────────────────────────────────────────────┤
│  [导出 PDF] [导出 Word] [分享] [重新执行]     │
└─────────────────────────────────────────────┘
```

### 8.4 错误处理

| 场景 | 前端表现 |
|------|---------|
| 网络断开 | Toast 提示 + 自动重连 |
| API 超时 | 加载状态 + "任务执行时间较长，请稍候..." + 可取消 |
| API 500 | 错误卡片 + 错误详情 + "重试"按钮 |
| 未登录 | 跳转登录页 |
| Token 过期 | 自动刷新，失败则跳转登录 |
| 权限不足 | 403 页面 + 说明 |
| 空状态 | 引导性文案 + 示例问题推荐 |

---

## 9. 测试规范

### 9.1 测试层级

```
L1: 单元测试 (覆盖率目标: ≥ 80%)
  - 工具函数
  - 数据模型验证
  - API 路由逻辑

L2: 集成测试
  - API 端到端测试 (Mock LLM)
  - 数据库操作测试
  - Agent 编排流程测试

L3: E2E 测试
  - 前端关键用户流程 (Playwright)
  - 登录→创建任务→查看结果

L4: 质量评测
  - Agent 输出质量 (LLM-as-Judge)
  - Commander 编排合理性
  - Skill 执行准确率
```

### 9.2 Agent 输出质量评测

```python
# LLM-as-Judge 评测维度
EVALUATION_RUBRIC = {
    "accuracy": {
        "weight": 0.35,
        "criteria": ["数据准确性", "计算正确性", "来源可靠性"]
    },
    "completeness": {
        "weight": 0.25,
        "criteria": ["覆盖所有要求维度", "无遗漏关键信息"]
    },
    "structure": {
        "weight": 0.15,
        "criteria": ["格式规范", "层次清晰", "可读性"]
    },
    "actionability": {
        "weight": 0.15,
        "criteria": ["结论明确", "论据充分", "投资决策可用"]
    },
    "safety": {
        "weight": 0.10,
        "criteria": ["无投资建议", "无合规风险", "风险充分揭示"]
    }
}
```

### 9.3 测试数据管理

```
- 使用专门的测试租户和测试用户
- 测试数据集中在 test/fixtures/
- Mock LLM 响应: test/fixtures/llm_responses/
- Mock MCP 响应: test/fixtures/mcp_responses/
- 集成测试使用独立测试数据库
- E2E 测试使用独立 Docker 环境
```

---

## 10. 运维规范

### 10.1 环境管理

| 环境 | 用途 | 配置 |
|------|------|------|
| **dev** | 本地开发 | Docker Compose, 热重载 |
| **staging** | 预发布验证 | K8s 小集群, 真实 LLM, Mock 数据源 |
| **production** | 生产环境 | K8s 多 AZ, 全量配置 |

### 10.2 监控指标

```
业务指标:
  - 任务提交量 (按 Agent / 租户)
  - 任务成功率
  - 任务平均耗时 (P50/P95/P99)
  - Token 消耗量 (按 Agent / 租户)
  - DAU / MAU

技术指标:
  - API 延迟 (P50/P95/P99)
  - API 错误率
  - LLM 调用延迟
  - 数据库连接池利用率
  - Redis 内存使用率
  - 容器 CPU/内存

告警规则:
  - API 错误率 > 1%: P1
  - API P95 延迟 > 5s: P2
  - LLM 调用失败率 > 5%: P1
  - 数据库连接池 > 80%: P2
  - 磁盘使用率 > 85%: P2
```

### 10.3 日志规范

```json
// 结构化日志格式
{
  "timestamp": "2026-06-20T10:30:00.000Z",
  "level": "INFO",
  "logger": "app.services.orchestrator",
  "message": "Commander task completed",
  "extra": {
    "task_id": "task_xxx",
    "tenant_id": "tenant_xxx",
    "user_id": "user_xxx",
    "agent_calls": 4,
    "tokens_used": 80000,
    "elapsed_ms": 120000,
    "request_id": "req_xxx"
  }
}
```

### 10.4 Docker 部署规范

```yaml
# docker-compose.yml (生产简化版)
version: '3.8'
services:
  backend:
    build: ./backend
    ports: ["8001:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/finagent
      - REDIS_URL=redis://redis:6379/0
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL}
    depends_on: [db, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports: ["3001:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on: [backend]

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: finagent
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d finagent"]

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

### 10.5 CI/CD 流程

```
Git Push → GitHub Actions →
  1. Lint (ruff + eslint)
  2. Type Check (mypy + tsc)
  3. Unit Tests (pytest)
  4. Integration Tests (docker-compose)
  5. Build Images (docker build)
  6. Push to Registry
  7. Deploy to Staging
  8. Smoke Tests
  9. Deploy to Production (手动审批)
```

---

## 附录

### A. 环境变量清单

| 变量 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | ✅ | — |
| `REDIS_URL` | Redis 连接串 | ✅ | — |
| `LLM_API_KEY` | LLM API Key | ✅ | — |
| `LLM_BASE_URL` | LLM API 地址 | ✅ | — |
| `LLM_MODEL` | 默认模型名称 | ❌ | deepseek-chat |
| `JWT_SECRET_KEY` | JWT 签名密钥 | ✅ | — |
| `JWT_ALGORITHM` | JWT 算法 | ❌ | RS256 |
| `MCP_MARKET_DATA_TOKEN` | 行情数据 MCP Token | ❌ | — |
| `MCP_FINANCIAL_KEY` | 财务数据 MCP Key | ❌ | — |
| `LOG_LEVEL` | 日志级别 | ❌ | INFO |
| `CORS_ORIGINS` | 允许的跨域来源 | ❌ | http://localhost:3001 |
| `SENTRY_DSN` | Sentry 错误追踪 | ❌ | — |

### B. 依赖版本约束

```
# backend/requirements.txt
fastapi>=0.110.0,<1.0.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.25
asyncpg>=0.29.0
redis>=5.0.0
pydantic>=2.5.0
python-jose[cryptography]>=3.3.0
bcrypt==4.1.3
httpx>=0.26.0
alembic>=1.13.0
pgvector>=0.2.0
email-validator>=2.1.0
sse-starlette>=1.8.0
tenacity>=8.0.0
structlog>=24.0.0
```

### C. 参考文档
- [MCP Specification](https://modelcontextprotocol.io)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Next.js Documentation](https://nextjs.org/docs)
- [Anthropic Financial Services Repo](https://github.com/anthropics/financial-services)
- [阿里云百炼平台文档](https://help.aliyun.com/zh/model-studio)

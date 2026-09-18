# 交接记录：Claude Code 后端工程第一轮（2026-09-18）

> 依据协同计划的交接格式填写。本文由 Claude Code 写入 `docs/coordination/`（超出 `backend/**` 边界）。
> **跨边界原因**：协同计划规定"双方交接记录必须共享"，且该目录即计划中约定的交接记录存放处。
> **影响文件**：仅新增本文档，不改动 Codex 已持有的任何 `docs/**` 文件。
> **回滚方式**：直接删除本文档即可。

## 1. 本轮目标和完成情况

**目标**：在独立 worktree 中运行后端，补齐 requirements 与本地数据库启动验证；为尽调闭环链路、权限隔离、旧接口非回归建立可重复测试；修复发现的问题。

**完成情况**：全部完成。未发现需要修改应用代码的功能性缺陷（详见第 5 节观察项）。

| 验收标准（协同计划） | 结果 |
|---|---|
| 一份企业 PDF 能生成页码级证据 | ✅ 3 页 PDF → 3 条页码级证据（page_number 1/2/3 + location_label） |
| 生成结果至少包含一个带证据或"待核验"的行动建议 | ✅ 建议绑定证据且 status=needs_review |
| 新事件能返回受影响判断、受影响建议和证据缺口 | ✅ impact-preview 返回 affected_claim_ids / affected_recommendation_ids / evidence_gaps |
| 影响结果只有在人工操作后才转为待复核动作 | ✅ 预览后工作区建议数不变，需 POST /action-recommendations 显式转换 |
| 确认/驳回留下前后内容、状态、备注、用户和时间 | ✅ 审计记录含 previous/new content+status、review_note、user_id、created_at |
| 跨用户访问返回 404/403，不泄露资源存在性 | ✅ 全部越权路径 404；无凭证请求 403 |
| 原有报告和研究工作区接口通过非回归测试 | ✅ tasks/claims/assumptions/challenges/memos/reports/files/agents 全绿 |

## 2. 修改文件清单（分支 `backend/cc-round1`）

| 文件 | 变更 |
|---|---|
| `backend/requirements.txt` | asyncpg 0.29.0 → 0.30.0、bcrypt 4.1.3 → 4.2.1（宿主 Python 3.13 无旧版 wheel，源码编译失败；新 pin 在容器 3.12 已验证） |
| `backend/requirements-dev.txt` | 新增：`-r requirements.txt` + pytest 8.3.4 + pytest-asyncio 0.26.0 |
| `backend/pytest.ini` | 新增：asyncio 会话级事件循环配置 |
| `backend/tests/conftest.py` | 新增：测试库初始化、ASGI 客户端、认证辅助、LLM mock、公共搭建函数 |
| `backend/tests/test_diligence_chain.py` | 新增：尽调闭环端到端 + 输入校验 + LLM 故障映射（503/502） |
| `backend/tests/test_permission_isolation.py` | 新增：跨用户隔离（6 个场景） |
| `backend/tests/test_regression_old_api.py` | 新增：旧接口非回归（认证/任务/文件/判断/假设/挑战/备忘录/报告/Agent 目录/健康） |
| `backend/tests/fixtures/sample.pdf` | 新增：3 页测试 PDF（来自仓库 test-materials 样例的副本） |

## 3. API/schema/数据库变更

**无任何 API、schema、数据库结构变更。** 本轮只新增测试与依赖 pin 调整；API 契约与第一轮冻结契约一致。

## 4. 已执行的验证命令及结果

### 环境准备

```bash
# 测试库（docker Postgres 5433 端口）
docker exec agent-db-1 createdb -U finagent finagent_test
# 宿主 venv（Python 3.13.13）
python3 -m venv ~/.venvs/yijin-cc
~/.venvs/yijin-cc/bin/pip install -r backend/requirements-dev.txt
```

### 后端启动验证

```bash
DATABASE_URL=postgresql+asyncpg://finagent:finagent_dev@localhost:5433/finagent_test \
  ~/.venvs/yijin-cc/bin/uvicorn app.main:app --port 8321
# → GET /health 200 {"status":"ok"}；POST /api/auth/register 200（真实建表 14 张 + 注册落库）
```

### 测试套件（宿主 Python 3.13）

```bash
cd backend && ~/.venvs/yijin-cc/bin/python -m pytest -q
# → 20 passed, 118 warnings in 12.10s（连续两次运行结果一致，drop_all 清库可重复）
```

### 测试套件（容器 Python 3.12，与 Dockerfile 部署环境一致）

```bash
docker run --rm --network agent_default -v $PWD/backend:/app -w /app \
  -e DATABASE_URL=postgresql+asyncpg://finagent:finagent_dev@agent-db-1:5432/finagent_test \
  -e STORAGE_PATH=/tmp/cc-test-storage python:3.12-slim \
  bash -c "pip install -q -r requirements-dev.txt && python -m pytest -q"
# → 20 passed, 119 warnings in 9.16s
```

### 测试覆盖矩阵

- 链路：注册 → 建研究对象 → 上传 PDF（页码证据）→ generate-assets（判断/假设/挑战/备忘录/建议 + 生成审计）→ 建事件 → impact-preview（不落库）→ 人工转建议 → 确认 → 驳回（含无原因 400）→ 审计串联 generated→confirmed→rejected
- 校验：无材料 generate-assets 400；空事件 400；无判断无证据预览 502；模型不可用 503 / 非结构化 502；跨对象证据引用 400；非法复核状态 400
- 权限：B 对 A 的 subject/workspace/reports/events/impact-preview/action-recommendations/claims/文件证据/文件下载/任务 → 全部 404；B 的文件挂 A 的对象 → 404；B 的事件 id 配 A 的 subject id → 404；B 的列表均为空
- 回归：登录/错密码 401/重复注册 400；任务 search_references 读写；文件无研究对象路径 + 下载字节一致 + 非法类型 400 + 超 20MB 413；判断编辑/确认审计；假设确认；挑战越权 claim_id 404；备忘录；报告列表 + 下载 + 格式 404 + 跨用户 404；Agent 目录；health

## 5. 未解决问题和风险等级

| # | 问题 | 等级 | 说明 |
|---|---|---|---|
| 1 | 事件影响预览结果**不持久化** | 中 | 刷新后预览丢失，需重新调用 LLM；"影响结果持久化/回放"按计划属第二轮任务 |
| 2 | 同一事务生成的多条判断 `updated_at` 相同，workspace 与 impact-preview 的排序在 tie 时不稳定 | 低 | 影响预览中 C1/C2 编号与前端展示顺序可能不一致；建议第二轮在 ORDER BY 加稳定 tiebreaker（如 `id`） |
| 3 | 无证据索引的判断/建议会回退绑定第一条证据（`_asset_verification` 回退分支），标记 needs_review | 低 | 模型未引用却被绑定证据的语义需产品确认；未改动，避免破坏前端展示 |
| 4 | 未认证请求返回 403 而非 401（FastAPI `HTTPBearer` 缺凭证的默认行为） | 低 | 在验收允许范围（404/403）内；若需 401+WWW-Authenticate 需自定义异常处理 |
| 5 | passlib 1.7.4 在 bcrypt 4.x 下打 "error reading bcrypt version" 警告 | 低 | 仅警告，hash/verify 功能正常（测试覆盖）；passlib 已停维护，长期可评估迁移方案 |
| 6 | `start-research-stream` / Commander 编排 SSE 链路未做接口级测试（需真实 LLM） | 低 | 不在本轮测试清单内；LLM 层已用 mock 覆盖资产生成与影响分析两条主链路 |
| 7 | 测试库 `finagent_test` 与测试存储目录 `/tmp` 由测试自动管理，但测试库需手动 createdb 一次 | 低 | 已在 conftest 文档字符串注明；如需自动建库可后续加启动脚本 |

## 6. 对另一方的明确依赖

1. **API 契约无变化** — 前端可继续按现有契约开发；无需等待后端调整。
2. 请 Codex 在整合时注意：requirements 的两个 pin 变更（asyncpg 0.30.0 / bcrypt 4.2.1）在合并后会影响容器重建 — 属于依赖版本小幅升级，已在 3.12 容器验证。
3. 第二轮（影响结果持久化/回放、任务失败重试、审计查询、迁移兼容）需等 Codex 完成第一轮前端后同步启动；届时建议先冻结 risk #2 的排序 tiebreaker 方案再动 preview 持久化。

## 7. 是否允许合并

**允许合并 `backend/cc-round1` → `main`**（仅 backend 新增测试与依赖 pin，不触碰 frontend/docs/API 契约；宿主 3.13 与容器 3.12 双环境验证完整）。

建议由 Codex 在整合阶段执行合并，以便与产品主线同步验收。

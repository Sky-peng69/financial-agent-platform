"""百炼 Multi-Agent 编排引擎 —— Commander 模式

架构：
  Commander（规划层）→ Specialist Agents（执行层，并行）→ Report Synthesizer（汇总层）
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import (
    AGENTS_BY_NAME,
    build_commander_system_prompt,
    get_specialist_prompt,
)
from app.models import DocumentEvidence, FileStatus, ResearchFile, Task, TaskStatus
from app.services.llm import chat

COMMANDER_TIMEOUT = 60
SPECIALIST_TIMEOUT = 120  # 单个 Specialist 超时秒数
MAX_ATTACHMENT_FILES = 3
MAX_ATTACHMENT_CHARS_PER_FILE = 4000
MAX_ATTACHMENT_CHARS_TOTAL = 10000


async def _commit_with_retry(db: AsyncSession, max_retries: int = 3) -> None:
    """提交数据库事务，带指数退避重试"""
    for attempt in range(max_retries):
        try:
            await db.commit()
            return
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise


def _agent_display_name(agent_name: str) -> str:
    """获取 Agent 的中文显示名"""
    info = AGENTS_BY_NAME.get(agent_name)
    return info.display_name if info else agent_name


async def _build_file_context(
    db: AsyncSession,
    user_id: str,
    file_ids: list[str] | None = None,
) -> str:
    """将本次请求明确携带的附件作为上下文。"""
    if not file_ids:
        return ""

    files_result = await db.execute(
        select(ResearchFile)
        .where(ResearchFile.user_id == user_id)
        .where(ResearchFile.status == FileStatus.PARSED)
        .where(ResearchFile.id.in_(file_ids[:MAX_ATTACHMENT_FILES]))
    )
    files = files_result.scalars().all()
    if not files:
        return ""

    blocks: list[str] = []
    remaining = MAX_ATTACHMENT_CHARS_TOTAL
    for item in files:
        evidence_result = await db.execute(
            select(DocumentEvidence)
            .where(DocumentEvidence.file_id == item.id)
            .where(DocumentEvidence.user_id == user_id)
            .order_by(DocumentEvidence.chunk_index)
        )
        evidence_items = evidence_result.scalars().all()
        snippets = [
            f"【{evidence.location_label}】\n{evidence.text.strip()}"
            for evidence in evidence_items
            if evidence.text.strip()
        ]
        evidence_text = "\n\n".join(snippets)
        if not evidence_text:
            continue
        excerpt = evidence_text[: min(MAX_ATTACHMENT_CHARS_PER_FILE, remaining)]
        remaining -= len(excerpt)
        blocks.append(f"### {item.original_name}\n{excerpt}")
        if remaining <= 0:
            break

    if not blocks:
        return ""

    return (
        "## 已上传材料上下文\n"
        "以下内容来自用户已上传并解析的研究材料。请像阅读用户随问题附上的材料一样使用它们，"
        "不要暴露内部处理过程；涉及材料依据时可自然提及文件名或页码。\n\n"
        + "\n\n".join(blocks)
    )


def _with_file_context(user_input: str, file_context: str) -> str:
    if not file_context:
        return user_input
    return f"{user_input}\n\n---\n\n{file_context}"


# ============================================================
# 1. Commander：任务规划
# ============================================================

async def plan_analysis(user_input: str) -> dict[str, Any]:
    """Commander 分析用户请求，输出执行计划"""
    system_prompt = build_commander_system_prompt()

    content, _ = await chat(
        messages=[{"role": "user", "content": f"请为以下用户请求规划分析计划：\n\n{user_input}"}],
        system_prompt=system_prompt,
        enable_search=False,
    )

    # 提取 JSON（可能被 markdown 代码块包裹）
    json_str = content
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0]

    try:
        plan = json.loads(json_str.strip())
    except json.JSONDecodeError:
        # Commander 返回了非 JSON，作为简单问题处理
        plan = {
            "analysis_type": "general",
            "specialists_needed": ["report-synthesizer"],
            "subtasks": [
                {
                    "agent": "report-synthesizer",
                    "title": "综合分析",
                    "prompt": user_input,
                    "priority": 1,
                }
            ],
            "synthesis_instruction": "直接回答用户问题",
        }

    return plan


async def _plan_with_timeout(user_input: str) -> dict[str, Any]:
    """Commander 规划超时后降级为单报告合成任务，避免前端长时间无进展。"""
    try:
        return await asyncio.wait_for(plan_analysis(user_input), timeout=COMMANDER_TIMEOUT)
    except asyncio.TimeoutError:
        return {
            "analysis_type": "general",
            "specialists_needed": ["report-synthesizer"],
            "subtasks": [
                {
                    "agent": "report-synthesizer",
                    "title": "综合分析",
                    "prompt": user_input,
                    "priority": 1,
                }
            ],
            "synthesis_instruction": f"Commander 规划超时（>{COMMANDER_TIMEOUT}秒），直接生成高信号密度报告",
        }


# ============================================================
# 2. Specialist：执行单个分析任务
# ============================================================

async def run_specialist(agent_name: str, prompt: str) -> dict[str, Any]:
    """运行单个 Specialist Agent，返回结构化结果（DeepSeek 自动联网搜索）"""
    system_prompt = get_specialist_prompt(agent_name)

    if not system_prompt:
        return {
            "agent": agent_name,
            "status": "skipped",
            "content": f"Agent '{agent_name}' 未配置",
            "search_results": None,
        }

    content, search_results = await chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system_prompt,
    )

    return {
        "agent": agent_name,
        "status": "completed",
        "content": content,
        "search_results": search_results,
    }


async def _run_with_timeout(agent_name: str, prompt: str):
    """运行 Specialist，带超时保护"""
    try:
        return await asyncio.wait_for(
            run_specialist(agent_name, prompt),
            timeout=SPECIALIST_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return {
            "agent": agent_name,
            "status": "timeout",
            "content": f"分析超时（>{SPECIALIST_TIMEOUT}秒）",
        }


# ============================================================
# 3. 主流程：编排执行（同步版）
# ============================================================

async def run_orchestrated_analysis(
    user_input: str,
    title: str,
    user_id: str,
    db: AsyncSession,
    file_ids: list[str] | None = None,
) -> Task:
    """百炼模式：Commander 规划 → 并行执行 → 汇总报告"""
    analysis_input = _with_file_context(
        user_input,
        await _build_file_context(db, user_id, file_ids),
    )

    # Phase 1: Commander 规划
    plan = await _plan_with_timeout(analysis_input)
    subtasks = plan.get("subtasks", [])

    # Phase 2: 并行执行所有 Specialist（不含 report-synthesizer）
    execution_tasks = [
        t for t in subtasks if t["agent"] != "report-synthesizer"
    ]
    synthesize_task = next(
        (t for t in subtasks if t["agent"] == "report-synthesizer"), None
    )

    specialist_results = await asyncio.gather(
        *[
            _run_with_timeout(t["agent"], t["prompt"])
            for t in execution_tasks
        ],
        return_exceptions=True,
    )

    # 过滤异常
    results: list[dict] = []
    for i, r in enumerate(specialist_results):
        if isinstance(r, Exception):
            results.append({
                "agent": execution_tasks[i]["agent"],
                "status": "error",
                "content": str(r),
            })
        else:
            results.append(r)

    # Phase 3: 汇总合成
    synthesis_instruction = plan.get("synthesis_instruction", "")

    # 如果只有一个 Agent 返回了结果且没有 synthesize，直接返回
    if len(results) == 1 and not synthesize_task:
        final_output = results[0]["content"]
    else:
        # 用 report-synthesizer 汇总
        reports_text = "\n\n---\n\n".join(
            f"【{r['agent']}】分析报告：\n{r['content']}" for r in results
        )
        synthesize_prompt = (
            synthesize_task["prompt"] if synthesize_task else user_input
        )
        final_prompt = f"""汇总指令：{synthesis_instruction}

原始用户请求：{analysis_input}

以下各专家的分析结果：

{reports_text}

请生成一份高信号密度的综合研究报告：
1. 先给结论卡，再给依据、分析、风险与待核验。
2. 合并重复观点，删除背景铺垫、通用常识和装饰性总结。
3. 专家观点冲突时直接列出分歧，不强行调和。
4. 关键数字保留来源状态；来源不足不得改写成确定事实。
5. 每个章节只保留会改变结论的内容，全文控制在 1800-2800 个中文字符。
6. 表格最多 3 张，只用于关键对比、证据清单或风险矩阵。
7. 结尾保留“以上分析仅供参考，不构成投资建议”。"""

        final_result = await _run_with_timeout("report-synthesizer", final_prompt)
        final_output = final_result["content"]

    # Phase 4: 保存到数据库
    # 收集所有 Specialist 的搜索引用
    all_search_refs = []
    for r in results:
        sr = r.get("search_results")
        if sr and isinstance(sr, list):
            all_search_refs.extend(sr)
    search_refs_json = json.dumps(all_search_refs, ensure_ascii=False) if all_search_refs else None

    task = Task(
        id=str(uuid.uuid4()),
        user_id=user_id,
        agent_name="commander",
        title=title,
        input_data=json.dumps({
            "user_input": user_input,
            "plan": plan,
            "subtask_results": results,
        }, ensure_ascii=False),
        output_data=final_output,
        search_references=search_refs_json,
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await db.commit()

    return task


# ============================================================
# 4. 主流程：编排执行（SSE 流式进度版）
# ============================================================

async def run_orchestrated_analysis_sse(
    user_input: str,
    title: str,
    user_id: str,
    db: AsyncSession,
    file_ids: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """
    SSE 流式版百炼编排：实时推送进度事件。
    前端可以实时看到 Commander 规划 → 各 Specialist 启动/完成 → 汇总 → 完成。

    事件类型：
      phase        — 阶段变更 {phase, message}
      agent_start  — Agent 开始执行 {agent, display_name, title}
      agent_done   — Agent 执行完成 {agent, display_name, status}
      done         — 全部完成 {task_id, output_data, plan, subtask_results}
      error        — 出错 {message}
    """
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        user_id=user_id,
        agent_name="commander",
        title=title,
        input_data=user_input,
        status=TaskStatus.RUNNING,
    )
    db.add(task)
    await _commit_with_retry(db)

    try:
        analysis_input = _with_file_context(
            user_input,
            await _build_file_context(db, user_id, file_ids),
        )

        # ═══ Phase 1: Commander 规划 ═══
        yield {
            "type": "phase",
            "phase": "planning",
            "message": "AI Commander 正在理解问题、规划分析任务...",
        }

        plan = await _plan_with_timeout(analysis_input)
        subtasks = plan.get("subtasks", [])

        execution_tasks = [
            t for t in subtasks if t["agent"] != "report-synthesizer"
        ]
        synthesize_task = next(
            (t for t in subtasks if t["agent"] == "report-synthesizer"), None
        )

        # 构建执行阶段消息
        agent_names = [
            _agent_display_name(t["agent"]) for t in execution_tasks
        ]
        if synthesize_task:
            agent_names.append(_agent_display_name("report-synthesizer"))
        agents_str = "、".join(agent_names) if agent_names else "专家"

        yield {
            "type": "phase",
            "phase": "executing",
            "message": f"任务拆解完成，启动 {len(execution_tasks)} 个专家并行分析：{agents_str}",
            "plan": plan,  # 前端可直接渲染编排计划
        }

        # ═══ Phase 2: 并行执行 Specialist ═══
        # 先发送所有 agent_start 事件
        for t in execution_tasks:
            yield {
                "type": "agent_start",
                "agent": t["agent"],
                "display_name": _agent_display_name(t["agent"]),
                "title": t.get("title", ""),
            }

        # 用 as_completed 逐个等待完成，每完成一个就发送 agent_done
        agent_display_map = {
            t["agent"]: _agent_display_name(t["agent"])
            for t in execution_tasks
        }

        coros = [
            _run_with_timeout(t["agent"], t["prompt"])
            for t in execution_tasks
        ]

        results: list[dict] = []
        if coros:
            for coro in asyncio.as_completed(coros):
                result = await coro
                agent_name = result.get("agent", "unknown")
                yield {
                    "type": "agent_done",
                    "agent": agent_name,
                    "display_name": agent_display_map.get(agent_name, agent_name),
                    "status": result.get("status", "unknown"),
                }
                results.append(result)

        # ═══ Phase 3: 汇总合成 ═══
        synthesis_instruction = plan.get("synthesis_instruction", "")

        if len(results) == 0 and not synthesize_task:
            final_output = "未能获取任何分析结果，请重试。"
        elif len(results) == 0 and synthesize_task:
            # 所有 subtask 都是 report-synthesizer，直接运行它
            final_result = await _run_with_timeout(
                "report-synthesizer",
                synthesize_task["prompt"],
            )
            final_output = final_result["content"]
        elif len(results) == 1 and not synthesize_task:
            final_output = results[0]["content"]
        else:
            yield {
                "type": "phase",
                "phase": "synthesizing",
                "message": "正在汇总各专家分析结果，生成综合报告...",
            }

            reports_text = "\n\n---\n\n".join(
                f"【{r['agent']}】分析报告：\n{r['content']}" for r in results
            )
            synthesize_prompt = (
                synthesize_task["prompt"] if synthesize_task else user_input
            )
            final_prompt = f"""汇总指令：{synthesis_instruction}

原始用户请求：{analysis_input}

以下各专家的分析结果：

{reports_text}

请生成一份高信号密度的综合研究报告：
1. 先给结论卡，再给依据、分析、风险与待核验。
2. 合并重复观点，删除背景铺垫、通用常识和装饰性总结。
3. 专家观点冲突时直接列出分歧，不强行调和。
4. 关键数字保留来源状态；来源不足不得改写成确定事实。
5. 每个章节只保留会改变结论的内容，全文控制在 1800-2800 个中文字符。
6. 表格最多 3 张，只用于关键对比、证据清单或风险矩阵。
7. 结尾保留“以上分析仅供参考，不构成投资建议”。"""

            final_result = await _run_with_timeout("report-synthesizer", final_prompt)
            final_output = final_result["content"]

        # ═══ Phase 4: 保存到数据库 ═══
        # 收集所有 Specialist 的搜索引用
        all_search_refs: list[dict] = []
        for r in results:
            sr = r.get("search_results")
            if sr and isinstance(sr, list):
                all_search_refs.extend(sr)
        search_refs_json = json.dumps(all_search_refs, ensure_ascii=False) if all_search_refs else None

        task.input_data = json.dumps({
            "user_input": user_input,
            "plan": plan,
            "subtask_results": results,
        }, ensure_ascii=False)
        task.output_data = final_output
        task.search_references = search_refs_json
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        await _commit_with_retry(db)

        yield {
            "type": "done",
            "task_id": task.id,
            "output_data": final_output,
            "plan": plan,
            "subtask_results": results,
            "search_references": all_search_refs if all_search_refs else None,
        }

    except asyncio.CancelledError:
        try:
            task.status = TaskStatus.FAILED
            task.error_message = "客户端连接中断，研究任务已停止"
            task.completed_at = datetime.now(timezone.utc)
            await _commit_with_retry(db)
        except Exception:
            pass
        raise

    except Exception as e:
        # 异常：更新 failed Task，yield error
        try:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            await _commit_with_retry(db)
        except Exception:
            pass

        yield {
            "type": "error",
            "message": str(e),
            "task_id": task_id,
        }

    finally:
        if task.status == TaskStatus.RUNNING:
            try:
                task.status = TaskStatus.FAILED
                task.error_message = "任务执行中断，已停止继续等待"
                task.completed_at = datetime.now(timezone.utc)
                await _commit_with_retry(db)
            except Exception:
                pass

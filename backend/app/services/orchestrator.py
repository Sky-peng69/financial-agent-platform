"""百炼 Multi-Agent 编排引擎 —— Commander 模式

架构：
  Commander（规划层）→ Specialist Agents（执行层，并行）→ Report Synthesizer（汇总层）
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import (
    AGENTS_BY_NAME,
    build_commander_system_prompt,
    get_specialist_prompt,
)
from app.models import ResearchFile, Task, TaskStatus
from app.services.llm import chat

SPECIALIST_TIMEOUT = 120  # 单个 Specialist 超时秒数
MAX_CONTEXT_FILES = 5
MAX_CONTEXT_CHARS_PER_FILE = 5000
MAX_CONTEXT_CHARS_TOTAL = 15000


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
    file_ids: list[str] | None,
) -> tuple[str, list[dict[str, str]]]:
    """读取用户选中的已解析文件，构造可注入模型的材料片段。"""
    if not file_ids:
        return "", []

    unique_ids = list(dict.fromkeys(file_ids))[:MAX_CONTEXT_FILES]
    result = await db.execute(
        select(ResearchFile)
        .where(ResearchFile.user_id == user_id)
        .where(ResearchFile.id.in_(unique_ids))
    )
    files_by_id = {item.id: item for item in result.scalars().all()}

    missing_ids = [file_id for file_id in unique_ids if file_id not in files_by_id]
    if missing_ids:
        raise ValueError("存在不可访问或不存在的研究材料")

    blocks: list[str] = []
    references: list[dict[str, str]] = []
    remaining = MAX_CONTEXT_CHARS_TOTAL
    for file_id in unique_ids:
        item = files_by_id[file_id]
        text = (item.extracted_text or "").strip()
        if not text:
            continue
        excerpt = text[: min(MAX_CONTEXT_CHARS_PER_FILE, remaining)]
        remaining -= len(excerpt)
        blocks.append(f"### 文件：{item.original_name}\n文件ID：{item.id}\n\n{excerpt}")
        references.append({
            "name": item.original_name,
            "snippet": excerpt[:200],
        })
        if remaining <= 0:
            break

    if not blocks:
        return "", references

    context = "\n\n".join(blocks)
    return (
        "## 用户上传研究材料\n"
        "以下内容来自用户上传文件，页码标记如【第 N 页】。"
        "分析时必须区分上传材料、公开检索和模型判断；引用上传材料时注明文件名和页码。\n\n"
        f"{context}",
        references,
    )


def _merge_user_input_with_file_context(user_input: str, file_context: str) -> str:
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
    file_ids: list[str] | None,
    db: AsyncSession,
) -> Task:
    """百炼模式：Commander 规划 → 并行执行 → 汇总报告"""
    file_context, file_references = await _build_file_context(db, user_id, file_ids)
    analysis_input = _merge_user_input_with_file_context(user_input, file_context)

    # Phase 1: Commander 规划
    plan = await plan_analysis(analysis_input)
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

请按标准报告格式生成综合报告。"""

        final_result = await run_specialist("report-synthesizer", final_prompt)
        final_output = final_result["content"]

    # Phase 4: 保存到数据库
    # 收集所有 Specialist 的搜索引用
    all_search_refs = [*file_references]
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
            "file_ids": file_ids or [],
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
    file_ids: list[str] | None,
    db: AsyncSession,
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
        file_context, file_references = await _build_file_context(db, user_id, file_ids)
        analysis_input = _merge_user_input_with_file_context(user_input, file_context)

        # ═══ Phase 1: Commander 规划 ═══
        yield {
            "type": "phase",
            "phase": "planning",
            "message": "AI Commander 正在理解问题、读取研究材料、规划分析任务...",
        }

        plan = await plan_analysis(analysis_input)
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
            final_result = await run_specialist("report-synthesizer", synthesize_task["prompt"])
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

请按标准报告格式生成综合报告。"""

            final_result = await run_specialist("report-synthesizer", final_prompt)
            final_output = final_result["content"]

        # ═══ Phase 4: 保存到数据库 ═══
        # 收集所有 Specialist 的搜索引用
        all_search_refs: list[dict] = [*file_references]
        for r in results:
            sr = r.get("search_results")
            if sr and isinstance(sr, list):
                all_search_refs.extend(sr)
        search_refs_json = json.dumps(all_search_refs, ensure_ascii=False) if all_search_refs else None

        task.input_data = json.dumps({
            "user_input": user_input,
            "file_ids": file_ids or [],
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

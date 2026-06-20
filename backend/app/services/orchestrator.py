"""百炼 Multi-Agent 编排引擎 —— Commander 模式

架构：
  Commander（规划层）→ Specialist Agents（执行层，并行）→ Report Synthesizer（汇总层）
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import (
    build_commander_system_prompt,
    get_specialist_prompt,
)
from app.models import Task, TaskStatus
from app.services.llm import get_client

SPECIALIST_TIMEOUT = 120  # 单个 Specialist 超时秒数


# ============================================================
# 1. Commander：任务规划
# ============================================================

async def plan_analysis(user_input: str) -> dict[str, Any]:
    """Commander 分析用户请求，输出执行计划"""
    client = get_client()
    system_prompt = build_commander_system_prompt()

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下用户请求规划分析计划：\n\n{user_input}"},
        ],
        temperature=0.2,
        max_tokens=2048,
    )

    content = response.choices[0].message.content or "{}"

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
    """运行单个 Specialist Agent，返回结构化结果"""
    client = get_client()
    system_prompt = get_specialist_prompt(agent_name)

    if not system_prompt:
        return {
            "agent": agent_name,
            "status": "skipped",
            "content": f"Agent '{agent_name}' 未配置",
        }

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    return {
        "agent": agent_name,
        "status": "completed",
        "content": response.choices[0].message.content or "",
    }


# ============================================================
# 3. 主流程：编排执行
# ============================================================

async def run_orchestrated_analysis(
    user_input: str,
    title: str,
    user_id: str,
    db: AsyncSession,
) -> Task:
    """百炼模式：Commander 规划 → 并行执行 → 汇总报告"""

    # Phase 1: Commander 规划
    plan = await plan_analysis(user_input)
    subtasks = plan.get("subtasks", [])

    # Phase 2: 并行执行所有 Specialist（不含 report-synthesizer）
    execution_tasks = [
        t for t in subtasks if t["agent"] != "report-synthesizer"
    ]
    synthesize_task = next(
        (t for t in subtasks if t["agent"] == "report-synthesizer"), None
    )

    # 并行执行 Specialist，带超时保护
    async def run_with_timeout(agent_name: str, prompt: str):
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

    specialist_results = await asyncio.gather(
        *[
            run_with_timeout(t["agent"], t["prompt"])
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

原始用户请求：{user_input}

以下各专家的分析结果：

{reports_text}

请按标准报告格式生成综合报告。"""

        final_result = await run_specialist("report-synthesizer", final_prompt)
        final_output = final_result["content"]

    # Phase 4: 保存到数据库
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
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await db.commit()

    return task

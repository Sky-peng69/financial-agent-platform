"""Agent 运行引擎 —— 单 Agent 直接调用 + SSE 流式输出"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import get_specialist_prompt
from app.models import Task, TaskStatus
from app.services.llm import chat, chat_stream

# 用户消息模板（run_agent_stream 和 run_agent_sse 共用）
USER_MESSAGE_TEMPLATE = """## 任务
{title}

## 用户输入 / 上下文
{user_input}

## 输出要求
1. 请严格按照你的系统提示中规定的输出模板和表格规范生成报告
2. 先联网搜索获取最新数据，再基于数据进行分析
3. 所有关键数据必须用表格呈现，表格必须完整规范（含表头、单位、比较维度、数据来源）
4. 结论先行——每节开头给出核心判断，再展开细节
5. 用词精准专业，禁用模糊词（"较好""可能""大概"），用具体数据和明确判断替代
6. 以"---\\n*以上分析仅供参考，不构成投资建议。*"结尾"""


def _format_search_refs(search_results: list[dict] | None) -> str | None:
    """将搜索引用序列化为 JSON 字符串（存储到 Task），为 None 时返回 None"""
    if not search_results:
        return None
    return json.dumps(search_results, ensure_ascii=False)


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


async def run_agent_stream(
    agent_name: str,
    title: str,
    user_input: str,
    user_id: str,
    db: AsyncSession,
) -> Task:
    """同步运行单个 Agent 并返回 Task 对象（自动联网搜索）"""
    system_prompt = get_specialist_prompt(agent_name) or ""

    content, search_results = await chat(
        messages=[{"role": "user", "content": USER_MESSAGE_TEMPLATE.format(title=title, user_input=user_input)}],
        system_prompt=system_prompt,
    )

    task = Task(
        id=str(uuid.uuid4()),
        user_id=user_id,
        agent_name=agent_name,
        title=title,
        input_data=user_input,
        output_data=content,
        search_references=_format_search_refs(search_results),
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await _commit_with_retry(db)

    return task


async def run_agent_sse(
    agent_name: str,
    title: str,
    user_input: str,
    user_id: str,
    db: AsyncSession,
):
    """
    SSE 流式运行单个 Agent（DeepSeek 自动判断是否联网搜索）。
    先创建 Task (status=running)，流式产出 chunk，结束后更新 Task 并 yield 最终结果。
    异常时更新 Task 为 failed 并 yield error 事件，避免 Task 永久卡在 running。
    客户端断开连接时（GeneratorExit）在 finally 中兜底更新 Task 状态。
    """
    system_prompt = get_specialist_prompt(agent_name) or ""

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

    try:
        # 2) 流式调用 DeepSeek（自动联网搜索）
        full_output = ""
        search_results: list[dict] | None = None
        async for event in chat_stream(
            messages=[{"role": "user", "content": USER_MESSAGE_TEMPLATE.format(title=title, user_input=user_input)}],
            system_prompt=system_prompt,
        ):
            if event["type"] == "chunk":
                full_output += event["content"]
                yield {"type": "chunk", "content": event["content"]}
            elif event["type"] == "search_results":
                search_results = event["results"]

        # 3) 流结束，更新 Task 为 completed
        task.output_data = full_output
        task.search_references = _format_search_refs(search_results)
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        await _commit_with_retry(db)

        # 4) 最后 yield 任务 ID 和搜索引用，前端可据此跳转详情页和展示来源
        yield {
            "type": "done",
            "task_id": task.id,
            "search_references": search_results,
        }

    except Exception as e:
        # 异常：更新 Task 为 failed，yield error 事件给前端
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        await _commit_with_retry(db)
        yield {"type": "error", "message": str(e), "task_id": task.id}

    finally:
        # 兜底：如果客户端断开连接（GeneratorExit），Task 仍为 RUNNING 时标记为 failed
        # GeneratorExit 是 BaseException，不被 except Exception 捕获
        if task.status == TaskStatus.RUNNING:
            try:
                task.status = TaskStatus.FAILED
                task.error_message = "客户端断开连接，任务被中断"
                task.completed_at = datetime.now(timezone.utc)
                await _commit_with_retry(db)
            except Exception:
                pass  # 尽最大努力更新，失败则放弃

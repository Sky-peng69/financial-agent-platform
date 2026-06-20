"""Agent 运行引擎 —— 单 Agent 直接调用（向后兼容）"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import get_specialist_prompt
from app.models import Task, TaskStatus
from app.services.llm import get_client


async def run_agent_stream(
    agent_name: str,
    title: str,
    user_input: str,
    user_id: str,
    db: AsyncSession,
) -> Task:
    """同步运行单个 Agent 并返回 Task 对象"""
    system_prompt = get_specialist_prompt(agent_name) or ""
    client = get_client()

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"任务：{title}\n\n用户输入：{user_input}"},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    result = response.choices[0].message.content or ""

    task = Task(
        id=str(uuid.uuid4()),
        user_id=user_id,
        agent_name=agent_name,
        title=title,
        input_data=user_input,
        output_data=result,
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await db.commit()

    return task
from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


SYSTEM_PROMPT = """你是一个专业金融 AI 助手，运行在金融 Agent 平台中。
你的职责是帮助银行工作人员和投资者完成金融分析工作。

核心原则：
1. 所有分析必须基于数据，引用来源
2. 不做投资建议——标注"以上分析仅供参考，不构成投资建议"
3. 缺失数据标注为 [DATA_MISSING]，不猜测
4. 使用专业金融术语，但保持可读性
5. 输出结构化内容（Markdown 格式）

当用户要求生成 Excel/PPT 时，你输出结构化 JSON 数据供后端渲染。
"""


async def chat(messages: list[dict], model: str = "deepseek-chat") -> str:
    """调用 DeepSeek Chat API"""
    client = get_client()
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    response = await client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=0.3,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


async def chat_stream(messages: list[dict], model: str = "deepseek-chat"):
    """流式调用 DeepSeek Chat API"""
    client = get_client()
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    stream = await client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=0.3,
        max_tokens=4096,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

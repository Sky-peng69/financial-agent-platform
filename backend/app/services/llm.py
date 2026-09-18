from datetime import datetime, timezone, timedelta

from openai import APIError, AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def get_client() -> AsyncOpenAI:
    global _client
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置，无法执行 AI 分析。请配置 .env 后重启后端。")
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_request_timeout_seconds,
        )
    return _client


def _today_date() -> str:
    """返回北京时间当日日期字符串，注入 prompt 提醒模型时间上下文"""
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")


def get_system_prompt() -> str:
    """每次请求时动态生成最小系统提示词。"""
    return f"""你是 DeepSeek。
当前日期：{_today_date()}。

请按你原本的模型能力自然回答用户问题，不要套固定格式，不要把普通问题写成报告。
如果用户明确要求报告、表格、清单或特定格式，再按用户要求组织。
涉及实时行情、最新事件或需要最新资料的问题，可以使用联网搜索。
"""


def _provider_error(exc: APIError) -> RuntimeError:
    return RuntimeError("AI 服务暂不可用，请检查模型配置后重试")


async def chat(
    messages: list[dict],
    model: str = "deepseek-chat",
    enable_search: bool = True,
    system_prompt: str = "",
) -> tuple[str, list[dict] | None]:
    """
    调用 DeepSeek Chat API，默认启用联网搜索（和 DeepSeek 官网一样的行为）。
    模型会自动判断是否需要搜索，搜索时返回引用来源。

    system_prompt: 额外的系统提示词（会追加到全局 SYSTEM_PROMPT 之后），
                   用于注入 Specialist 角色提示词。

    返回 (content, search_results):
      - content: 模型回复文本（含格式化的搜索引用附录）
      - search_results: 原始搜索引用列表，或 None
    """
    client = get_client()
    full_system = get_system_prompt()
    if system_prompt:
        full_system += "\n\n" + system_prompt
    full_messages = [{"role": "system", "content": full_system}, *messages]

    extra: dict = {}
    if enable_search:
        extra["web_search_options"] = {"search_context_size": "medium"}

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.3,
            max_tokens=8192,
            extra_body=extra if extra else None,
        )
    except APIError as exc:
        raise _provider_error(exc) from exc
    content = response.choices[0].message.content or ""

    # 提取联网搜索引用（DeepSeek 返回在 message.search_results 或顶层）
    search_results = getattr(response.choices[0].message, "search_results", None)
    if not search_results:
        search_results = getattr(response, "search_results", None)
    if search_results and isinstance(search_results, list):
        ref_lines = ["\n\n---\n🔍 **联网搜索引用：**"]
        for r in search_results:
            name = r.get("name") or r.get("title") or "来源"
            url = r.get("url") or r.get("link") or ""
            snippet = r.get("snippet") or r.get("content") or ""
            ref_lines.append(f"- [{name}]({url})  — {snippet[:120]}")
        content += "\n".join(ref_lines)

    return content, search_results if isinstance(search_results, list) else None


async def chat_stream(
    messages: list[dict],
    model: str = "deepseek-chat",
    enable_search: bool = True,
    system_prompt: str = "",
):
    """
    流式调用 DeepSeek Chat API，默认启用联网搜索。
    模型自动判断是否搜索，流式返回时搜索引用会追加到最后。

    system_prompt: 额外的系统提示词（会追加到全局 SYSTEM_PROMPT 之后）。

    Yields dicts:
      {"type": "chunk", "content": "..."}   — 文本片段
      {"type": "search_results", "results": [...]}  — 联网搜索引用（流结束后，如有）
    """
    client = get_client()
    full_system = get_system_prompt()
    if system_prompt:
        full_system += "\n\n" + system_prompt
    full_messages = [{"role": "system", "content": full_system}, *messages]

    extra: dict = {}
    if enable_search:
        extra["web_search_options"] = {"search_context_size": "medium"}

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.3,
            max_tokens=8192,
            stream=True,
            extra_body=extra if extra else None,
        )
    except APIError as exc:
        raise _provider_error(exc) from exc

    collected_search_results: list[dict] = []

    async for chunk in response:
        # 尝试从 chunk 收集搜索引用（DeepSeek 可能在 delta 或顶层返回）
        delta = chunk.choices[0].delta
        sr = getattr(delta, "search_results", None) or getattr(chunk, "search_results", None)
        if sr and isinstance(sr, list):
            for item in sr:
                if item not in collected_search_results:
                    collected_search_results.append(item)

        if delta.content:
            yield {"type": "chunk", "content": delta.content}

    # 流结束后，如有搜索引用，yield 出来
    if collected_search_results:
        yield {"type": "search_results", "results": collected_search_results}

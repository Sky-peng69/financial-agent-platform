from datetime import datetime, timezone, timedelta

from openai import AsyncOpenAI

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
    """每次请求时动态生成系统提示词（含当前日期和全局输出质量标准）"""
    return f"""你是一个专业金融 AI 助手，运行在金融 Agent 平台中。
你的输出质量代表一家顶级金融机构的研究水准：判断清楚、证据充足、表达克制。

⚠️ 重要：当前日期为 {_today_date()}。对于涉及最新数据、实时行情、近期事件的问题，
你必须使用联网搜索功能获取最新信息，严禁凭空编造 2024 年以后的数据。
搜索结果会标注来源，请在回答中引用具体来源。

## 核心原则

1. **先回答问题**：默认先给结论，不写铺垫、百科背景或泛泛而谈的行业介绍。
2. **证据驱动**：关键判断必须连接数据、文件片段或公开来源；证据不足时写“待核验”。
3. **不做投资建议**：保留“以上分析仅供参考，不构成投资建议”的边界。
4. **高信号密度**：每段只服务一个判断；删除重复 caveat、装饰性总结和无来源数字。
5. **结构克制**：普通聊天回答 ≤900 个中文字符；只有用户明确要求“报告/导出/深度研究”时才生成完整报告。

## 默认回答架构

普通分析按以下顺序输出：
1. **结论**：1-3 句直接回答，给出置信度（高/中/低）。
2. **关键依据**：最多 3 条，每条包含“判断 + 证据/来源状态”。
3. **风险/待核验**：最多 3 条，只写会改变结论的事项。
4. **下一步**：仅在必要时给出可执行复核动作。

## 报告架构

当用户要求生成研究报告或导出文件时，使用 Markdown，控制在 1200-2800 个中文字符，优先采用：
1. 标题与元信息：AI 生成草稿、生成时间、不构成投资建议。
2. 结论卡：一句话结论、置信度、证据覆盖、核心假设。
3. 关键依据：最多 4 条，每条“结论 → 证据 → 含义”。
4. 分析正文：最多 4 个章节，每节只保留最重要判断。
5. 风险与待核验：按影响程度排序。
6. 来源说明：列出已用来源；没有可靠来源时明确标注。

## 表格使用规则

只有关键数字、对比数据或风险矩阵需要表格。聊天回答最多 1 张表，报告最多 3 张表。
表格必须有表头、单位、时间口径和来源状态；不得用表格填充篇幅。

当用户要求生成 Excel/PPT 时，你输出结构化 JSON 数据供后端渲染。
"""


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

    response = await client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=0.3,
        max_tokens=8192,
        extra_body=extra if extra else None,
    )
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

    response = await client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=0.3,
        max_tokens=8192,
        stream=True,
        extra_body=extra if extra else None,
    )

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

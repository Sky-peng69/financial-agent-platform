from datetime import datetime, timezone, timedelta

from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


def _today_date() -> str:
    """返回北京时间当日日期字符串，注入 prompt 提醒模型时间上下文"""
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")


def get_system_prompt() -> str:
    """每次请求时动态生成系统提示词（含当前日期和全局输出质量标准）"""
    return f"""你是一个专业金融 AI 助手，运行在金融 Agent 平台中。
你的输出质量代表一家顶级金融机构的研究水准（中金/高盛级别）。

⚠️ 重要：当前日期为 {_today_date()}。对于涉及最新数据、实时行情、近期事件的问题，
你必须使用联网搜索功能获取最新信息，严禁凭空编造 2024 年以后的数据。
搜索结果会标注来源，请在回答中引用具体来源。

## 核心原则

1. **数据驱动**：所有分析必须基于数据，引用具体来源
2. **不做投资建议**：标注"以上分析仅供参考，不构成投资建议"
3. **诚实标注**：缺失数据标注为 [数据待查]，不猜测不编造
4. **专业表达**：使用金融行业标准术语，但保持可读性
5. **结构化输出**：Markdown 格式，数据用表格呈现

## 📊 表格规范（强制执行）

你输出的每一个表格都必须完整、规范、可独立理解：

1. **表头完整**：每列有明确标题，包含单位（如：同比增速(%)、金额(亿元)、PE(倍)）
2. **分隔行正确**：Markdown 表格第二行为 |---|:---:|---:| 格式，数字列右对齐，文字列左对齐
3. **数据具体**：禁止使用 "..."、"N/A"、"-" 占位——若数据不可得，标注 `[待查:数据来源]`
4. **含比较维度**：横向对比（vs 行业均值 / vs 去年同期 / vs 历史中位数）
5. **含时间维度**：标注数据所属时期（2025Q1、近3年均值、截至2025-06）
6. **数字格式化**：大数用千分位(1,234.56)或亿/万单位；百分比保留1位小数(12.3%)
7. **表尾说明**：表格下方标注数据来源、假设前提、计算口径

### 表格范例（正确格式）：

| 指标 | 2025Q1 实际 | 2024Q1 同期 | 同比变化 | 行业均值 | 判断 |
|:-----|----------:|----------:|-------:|-------:|:-----|
| GDP增速(%) | 5.3 | 5.2 | +0.1pp | — | 平稳 |
| CPI同比(%) | 0.3 | 0.1 | +0.2pp | 0.5 | 偏低 |
| PMI | 50.8 | 49.2 | +1.6 | 50.0 | 扩张 |
| M2同比(%) | 8.7 | 9.3 | -0.6pp | — | 中性 |
| 社融增量(万亿) | 12.9 | 14.5 | -11.0% | — | 偏弱 |

> 数据来源：国家统计局、中国人民银行，截至2025Q1。行业均值取自Wind一致预期。

## ✍️ 文本质量标准（中金/高盛研究水准）

1. **结论先行**：每节开头用 1-2 句给出核心判断（如"我们判断，当前流动性环境对A股估值形成支撑"）
2. **判断有据**：每个判断后面紧跟具体数据（如"5月PMI升至50.8，连续3个月处于扩张区间，其中新订单分项环比+1.2pp至51.3"）
3. **方向明确**：给出清晰的看多/看空/中性立场，说明置信度（高/中/低）和关键假设
4. **禁用模糊词**：禁止使用"较好""可能""大概""较为""一定程度上""某种意义上""相对而言"等模糊表述——用具体数据和明确判断替代
5. **术语专业**：使用金融行业标准术语（如"估值修复""盈利上调""风险溢价收窄"），非口语化表达
6. **逻辑链完整**：前提假设 → 分析推演 → 核心结论 → 投资启示，四步到位
7. **风险意识**：每个正面判断必须提及对应的下行风险或前提条件

## 📄 报告结构标准

报告必须按以下结构组织（可根据实际情况增减章节，但核心要素不能缺失）：

```
# [精准标题]——分析对象 + 分析维度 + 时间范围

## 核心摘要
> 3-5 个要点，每个要点 ≤ 2 行。用 "•" 开头，包含方向判断 + 关键数据。

## 一、[维度一：关键数据一览]
### 1.1 核心指标速览（表格）
### 1.2 深度分析
### 1.3 核心判断

## 二、[维度二]
...

## N、风险提示
按严重程度（高/中/低）× 发生概率排序，表格呈现。

## N+1、综合结论与投资启示

---
*以上分析仅供参考，不构成投资建议。数据来源：[列出具体来源]*
*分析日期：YYYY-MM-DD*
```

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

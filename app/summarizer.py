from openai import AsyncOpenAI, BadRequestError

from app.config import settings

_WORDS_COUNT = 25
_LANGUAGE = "Chinese"
_OUTLINE = True
_EMOJI = True

_SYSTEM_PROMPT = (
    "你是一位专业的视频内容分析师，擅长从视频字幕中提炼核心要点并生成结构化摘要。"
    "请自动纠正字幕中可能存在的错别字和语音识别错误，用中文输出。"
)


def _compute_sentence_count(transcript: str) -> int:
    n = len(transcript)
    if n < 500:
        return 3
    if n < 2000:
        return 4
    if n < 8000:
        return 6
    if n < 20000:
        return 8
    return 10


def _build_user_message(title: str, transcript: str, sentence_count: int) -> str:
    outline_description = (
        "每个 Highlight 要点下写 1-2 条子要点展开说明。\n"
        if _OUTLINE
        else ""
    )
    emoji_description = (
        "每个 Highlight 要点前加一个贴切的 Emoji。\n"
        if _EMOJI
        else ""
    )
    return (
        f'标题："{title}"\n'
        f'字幕："{transcript}"\n'
        "\n"
        "请按以下模板输出：\n"
        "\n"
        "## 一句话总结\n"
        "（一句话，20 字以内，概括视频绝对核心）\n"
        "\n"
        "## Summary\n"
        "（2-3 句话整体概述）\n"
        "\n"
        "## Highlights\n"
        "- [Emoji] 核心要点\n"
        "    - 子要点\n"
        "\n"
        "## 精华摘录\n"
        "- 关键数据 / 金句 / 重要细节\n"
        "\n"
        "写作要求：\n"
        f"1. TL;DR：一句话（20 字以内）点明核心。\n"
        f"2. Summary：2-3 句话整体概述视频内容。\n"
        f"3. Highlights：恰好 {sentence_count} 个要点，每条至少 {_WORDS_COUNT} 个汉字。\n"
        f"{outline_description}"
        f"{emoji_description}"
        f"4. 精华摘录：提取 1-3 条关键数据、金句或令人印象深刻的细节，原文引用优先。\n"
        "\n"
        f"请用{_LANGUAGE}输出。"
    )


async def summarize(title: str, transcript: str) -> str:
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com",
    )

    # 限制 transcript 长度，避免超出 token 限制（约 30 万字符）
    max_transcript_len = 300_000
    if len(transcript) > max_transcript_len:
        transcript = transcript[:max_transcript_len] + "\n\n[内容过长，已截断]"

    sentence_count = _compute_sentence_count(transcript)

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(title, transcript, sentence_count)},
            ],
            temperature=1,
            max_tokens=4096,
        )
    except BadRequestError as exc:
        if "Content Exists Risk" in str(exc):
            raise RuntimeError(
                "视频内容触发了 LLM 内容审核，无法生成总结。"
                "请尝试其他视频。"
            ) from exc
        raise

    return response.choices[0].message.content

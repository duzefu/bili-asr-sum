from openai import AsyncOpenAI, BadRequestError

from app.config import settings

_SENTENCE_COUNT = 6
_WORDS_COUNT = 35
_LANGUAGE = "Chinese"
_OUTLINE = True
_EMOJI = True


def _build_user_message(title: str, transcript: str) -> str:
    outline_description = (
        "Write all bullet points in outline style with child points for each highlight.\n"
        if _OUTLINE
        else ""
    )
    emoji_description = (
        "Use an appropriate Emoji at the start of each bullet point.\n"
        if _EMOJI
        else ""
    )
    return (
        f'Title: "{title}"\n'
        f'Transcript: "{transcript}"\n'
        "\n"
        "Instructions:\n"
        "Your output should use the following template:\n"
        "## Summary\n"
        "## Highlights\n"
        "- [Emoji] Bulletpoint\n"
        "    - Child points\n"
        "\n"
        f"Your task is to summarise the text I have given you in up to {_SENTENCE_COUNT} concise bullet points, "
        f"starting with a short highlight, each bullet point is at least {_WORDS_COUNT} words.\n"
        f"{outline_description}"
        f"{emoji_description}"
        "Use the text above: {Title} {Transcript}.\n"
        "\n"
        f"Reply in {_LANGUAGE} Language."
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

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": _build_user_message(title, transcript)},
            ],
            temperature=1,
            max_tokens=4096,
        )
    except BadRequestError as exc:
        if "Content Exists Risk" in str(exc):
            raise RuntimeError(
                "视频内容触发了 DeepSeek 内容审核，无法生成总结。"
                "请尝试其他视频。"
            ) from exc
        raise

    return response.choices[0].message.content

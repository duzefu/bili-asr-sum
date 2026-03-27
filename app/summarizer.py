from openai import AsyncOpenAI

from app.config import settings

_SYSTEM_PROMPT = """你是一个专业的视频内容总结助手。请根据提供的视频标题和转录内容，生成简洁清晰的中文总结。

总结格式：
1. **核心主题**：一句话概括视频主题
2. **主要内容**：3-5个要点（用 • 符号列出）
3. **关键结论**：视频的核心观点或结论

要求：语言简洁，重点突出，忽略无意义的重复内容和口头禅。"""


async def summarize(title: str, transcript: str) -> str:
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com",
    )

    # 限制 transcript 长度，避免超出 token 限制（约 30 万字符）
    max_transcript_len = 300_000
    if len(transcript) > max_transcript_len:
        transcript = transcript[:max_transcript_len] + "\n\n[内容过长，已截断]"

    user_message = f"视频标题：{title}\n\n转录内容：\n{transcript}"

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    return response.choices[0].message.content

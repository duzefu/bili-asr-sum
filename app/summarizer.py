from openai import AsyncOpenAI

from app.config import settings

_SYSTEM_PROMPT = """你是一位专业的视频内容编辑和笔记专家。现在我将提供一段 YouTube 或 Bilibili 视频的完整字幕/转录文本。

请严格按照以下要求处理：

1. **整体总结**：先用 1-2 段话给出视频的核心主题和主要观点（控制在 150 字以内）。
2. **分节重写**：按视频内容的逻辑主题，将全文重写成“阅读版本”，分成若干小节。每小节用清晰的小标题（用 **粗体** 或 ## 标记），并在小标题后注明大致时间戳（如果字幕带有时间信息，如 [00:00]）。
3. **关键要点**：每个小节末尾用 bullet points（- 或 •）列出 3-5 个最重要/最 actionable 的要点。
4. **额外价值**：最后添加一个“核心 takeaway”部分，总结视频最值得记住的 1-3 个洞见或行动建议。
5. **风格要求**：语言简洁流畅、专业且易懂，避免口语化重复；使用中文输出；保持客观中立；如果有数据、列表或步骤，要完整保留并清晰呈现。你是一个专业的视频内容总结助手。请根据提供的视频标题和转录内容，生成简洁清晰的中文总结。

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

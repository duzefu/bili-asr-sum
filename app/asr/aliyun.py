import asyncio
from pathlib import Path

import dashscope
from dashscope.audio.asr import Recognition

from app.asr.base import ASRProvider


class AliyunASR(ASRProvider):
    """
    阿里云 DashScope SenseVoice 语音识别。
    使用 DashScope Python SDK，直接接受本地文件路径，无需公网 URL。
    文档：https://help.aliyun.com/zh/model-studio/sensevoice
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ALIYUN_DASHSCOPE_API_KEY 未配置")
        dashscope.api_key = api_key

    async def transcribe(self, audio_path: Path) -> str:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: Recognition.call(
                model="sensevoice-v1",
                file=str(audio_path),
                format="mp3",
                sample_rate=16000,
                language_hints=["zh", "en"],
            ),
        )
        if response.status_code != 200:
            raise RuntimeError(f"阿里云 ASR 失败: {response.message}")
        return self._extract_text(response.output)

    def _extract_text(self, output) -> str:
        # sentence_info 是主要格式
        sentences = getattr(output, "sentence_info", None) or []
        texts = [
            (s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")).strip()
            for s in sentences
        ]
        texts = [t for t in texts if t]
        if texts:
            return "\n".join(texts)

        # fallback: result 列表格式
        results = getattr(output, "result", None) or []
        texts = [
            (r.get("text", "") if isinstance(r, dict) else getattr(r, "text", "")).strip()
            for r in results
        ]
        return "\n".join(t for t in texts if t)

import asyncio
import threading
from pathlib import Path

from app.asr.base import ASRProvider


class LocalSenseVoiceASR(ASRProvider):
    """
    本地 SenseVoice-Small 语音识别（离线，无需 API Key）。
    依赖：pip install funasr modelscope torch torchaudio
    首次运行会自动从 ModelScope 下载模型到 ~/.cache/modelscope/
    文档：https://github.com/FunAudioLLM/SenseVoice
    """

    def __init__(self, device: str = "cpu", language: str = "auto"):
        """
        device: "cpu" / "cuda:0" / "mps" 等
        language: "auto" | "zh" | "en" | "ja" | "ko" | "yue"
        """
        self.language = language
        self._model = None
        self._device = device
        self._lock = threading.Lock()

    def _load_model(self):
        """延迟加载，避免进程启动时占用过多时间/内存。"""
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from funasr import AutoModel  # type: ignore

            self._model = AutoModel(
                model="iic/SenseVoiceSmall",
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": 30000},
                device=self._device,
            )

    async def transcribe(self, audio_path: Path) -> str:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._run_inference, audio_path)
        return result

    def _run_inference(self, audio_path: Path) -> str:
        self._load_model()
        res = self._model.generate(
            input=str(audio_path),
            language=self.language,
            use_itn=True,          # 数字/标点规整化
            batch_size_s=300,      # 每批最多 300s 音频
        )
        if not res:
            return ""
        # res 是 list[dict]，每个 dict 有 "text" 字段
        texts = [r.get("text", "").strip() for r in res if r.get("text", "").strip()]
        return "\n".join(texts)

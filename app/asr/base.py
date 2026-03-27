from abc import ABC, abstractmethod


class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_url: str) -> str:
        """
        提交音频文件 URL 进行识别，轮询直到完成，返回转录文本。
        audio_url 必须是 ASR 服务可公网访问的 HTTP/HTTPS URL。
        """
        ...

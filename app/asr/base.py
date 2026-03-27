from abc import ABC, abstractmethod
from pathlib import Path


class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> str:
        """
        接收本地音频文件路径，返回转录文本。
        """
        ...

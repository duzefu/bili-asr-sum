import asyncio
import httpx

from app.asr.base import ASRProvider

# DashScope FunASR 录音文件识别 API
_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"


class AliyunASR(ASRProvider):
    """
    阿里云 DashScope FunASR 录音文件识别（异步批量模式）。
    文档：https://help.aliyun.com/zh/model-studio/funauidio-asr-recorded-speech-recognition-python-sdk
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ALIYUN_DASHSCOPE_API_KEY 未配置")
        self._api_key = api_key

    async def transcribe(self, audio_url: str) -> str:
        task_id = await self._submit(audio_url)
        return await self._poll(task_id)

    async def _submit(self, audio_url: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": "paraformer-v2",
            "input": {
                "file_urls": [audio_url],
            },
            "parameters": {
                "language_hints": ["zh", "en"],
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_SUBMIT_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("output", {}).get("task_status") == "Failed":
            raise RuntimeError(f"阿里云 ASR 提交失败: {data}")

        task_id = data["output"]["task_id"]
        return task_id

    async def _poll(self, task_id: str) -> str:
        query_url = f"{_SUBMIT_URL}/{task_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await client.get(query_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("output", {}).get("task_status", "")

                if status == "SUCCEEDED":
                    results = data["output"].get("results", [])
                    if not results:
                        raise RuntimeError("阿里云 ASR 返回空结果")
                    # 获取转录结果文件 URL
                    transcription_url = results[0].get("transcription_url")
                    if not transcription_url:
                        raise RuntimeError("阿里云 ASR 未返回 transcription_url")
                    return await self._fetch_transcript(transcription_url, client)

                elif status == "FAILED":
                    raise RuntimeError(f"阿里云 ASR 识别失败: {data.get('output', {}).get('message', '')}")

                # PENDING 或 RUNNING，继续等待
                await asyncio.sleep(5)

    async def _fetch_transcript(self, url: str, client: httpx.AsyncClient) -> str:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # 提取所有句子的文字并拼接
        texts = []
        for item in data.get("transcripts", []):
            for sentence in item.get("sentences", []):
                text = sentence.get("text", "").strip()
                if text:
                    texts.append(text)

        if not texts:
            # fallback：直接取 text 字段
            for item in data.get("transcripts", []):
                t = item.get("text", "").strip()
                if t:
                    texts.append(t)

        return "\n".join(texts)

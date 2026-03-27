import asyncio
import base64
from pathlib import Path

import httpx

from app.asr.base import ASRProvider

_SUBMIT_URL = "https://openspeech.bytedance.com/api/v1/auc/submit"
_QUERY_URL = "https://openspeech.bytedance.com/api/v1/auc/query"


class VolcengineASR(ASRProvider):
    """
    火山引擎豆包语音识别（录音文件识别标准版）。
    通过 base64 编码直接传输音频数据，无需公网 URL。
    文档：https://www.volcengine.com/docs/6561/80820
    音频要求：mp3/wav/ogg，采样率 16000Hz
    """

    def __init__(self, app_id: str, access_token: str):
        if not app_id or not access_token:
            raise ValueError("VOLCENGINE_APP_ID / VOLCENGINE_ACCESS_TOKEN 未配置")
        self._app_id = app_id
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Resource-Id": "volc.sauc.offline",
        }

    async def transcribe(self, audio_path: Path) -> str:
        task_id = await self._submit(audio_path)
        return await self._poll(task_id)

    async def _submit(self, audio_path: Path) -> str:
        audio_data = base64.b64encode(audio_path.read_bytes()).decode()
        payload = {
            "appid": self._app_id,
            "language": "zh-CN",
            "audio_format": "mp3",
            "audio_data": audio_data,
            "enable_punctuation": True,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(_SUBMIT_URL, json=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0 and data.get("resp", {}).get("code") != 0:
            raise RuntimeError(f"火山引擎 ASR 提交失败: {data}")

        task_id = (
            data.get("id") or
            data.get("task_id") or
            data.get("resp", {}).get("id")
        )
        if not task_id:
            raise RuntimeError(f"火山引擎 ASR 未返回 task_id: {data}")
        return task_id

    async def _poll(self, task_id: str) -> str:
        params = {"appid": self._app_id, "id": task_id}

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await client.get(_QUERY_URL, params=params, headers=self._headers)
                resp.raise_for_status()
                data = resp.json()

                # task_status: 0=处理中, 1=成功, 2=失败
                resp_data = data.get("resp", data)
                status = resp_data.get("task_status", resp_data.get("status", -1))

                if status == 1:
                    return self._extract_text(resp_data)
                elif status == 2:
                    raise RuntimeError(f"火山引擎 ASR 识别失败: {data}")

                await asyncio.sleep(5)

    def _extract_text(self, data: dict) -> str:
        utterances = data.get("utterances", [])
        if utterances:
            return "\n".join(u.get("text", "") for u in utterances if u.get("text"))

        text = data.get("text", "") or data.get("result", {}).get("text", "")
        return text

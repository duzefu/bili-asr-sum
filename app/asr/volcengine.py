import asyncio
import base64
from pathlib import Path
import uuid

import httpx

from app.asr.base import ASRProvider

_RECOGNIZE_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
_SUCCESS_CODE = "20000000"
_PROCESSING_CODES = {"20000001", "20000002"}


class VolcengineASR(ASRProvider):
    """
    火山引擎豆包语音识别（大模型录音文件极速版）。
    通过 base64 直接上传本地音频，无需公网 URL。
    官方文档：
    - 极速版：https://www.volcengine.com/docs/6561/1631584
    - 标准版：https://www.volcengine.com/docs/6561/1354868
    限制：单文件不超过 2 小时、100MB。
    """

    def __init__(self, app_id: str, access_token: str, resource_id: str):
        if not app_id or not access_token or not resource_id:
            raise ValueError(
                "VOLCENGINE_APP_ID / VOLCENGINE_ACCESS_TOKEN / VOLCENGINE_RESOURCE_ID 未配置"
            )
        self._app_id = app_id
        self._access_token = access_token
        self._resource_id = resource_id

    def _headers(self, request_id: str) -> dict:
        return {
            "X-Api-App-Key": self._app_id,
            "X-Api-Access-Key": self._access_token,
            "X-Api-Resource-Id": self._resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json",
        }

    async def transcribe(self, audio_path: Path) -> str:
        request_id = str(uuid.uuid4())
        audio_data = base64.b64encode(audio_path.read_bytes()).decode()
        payload = {
            "user": {
                "uid": self._app_id,
            },
            "audio": {
                "data": audio_data,
                "format": self._detect_audio_format(audio_path),
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
            },
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(_RECOGNIZE_URL, json=payload, headers=self._headers(request_id))

        if resp.status_code >= 400:
            raise RuntimeError(self._format_http_error(resp))

        status_code = resp.headers.get("X-Api-Status-Code", "")
        if status_code in _PROCESSING_CODES:
            await asyncio.sleep(1)
        if status_code != _SUCCESS_CODE:
            raise RuntimeError(self._format_api_error(resp))

        data = resp.json()
        text = self._extract_text(data)
        if not text.strip():
            raise RuntimeError(self._format_api_error(resp, message="火山引擎 ASR 返回空文本"))
        return text

    def _extract_text(self, data: dict) -> str:
        result = data.get("result", data)
        utterances = result.get("utterances", [])
        if utterances:
            return "\n".join(u.get("text", "") for u in utterances if u.get("text"))

        text = result.get("text", "")
        return text

    def _detect_audio_format(self, audio_path: Path) -> str:
        ext = audio_path.suffix.lower().lstrip(".")
        if ext in {"mp3", "wav", "ogg"}:
            return ext
        raise ValueError(f"火山引擎 ASR 暂不支持的音频格式: {audio_path.suffix}")

    def _format_http_error(self, resp: httpx.Response) -> str:
        body = resp.text.strip()
        logid = resp.headers.get("X-Tt-Logid", "")
        extra = f", logid={logid}" if logid else ""
        if body:
            return f"火山引擎 ASR HTTP {resp.status_code}{extra}: {body}"
        return f"火山引擎 ASR HTTP {resp.status_code}{extra}"

    def _format_api_error(self, resp: httpx.Response, message: str | None = None) -> str:
        status_code = resp.headers.get("X-Api-Status-Code", "unknown")
        api_message = resp.headers.get("X-Api-Message", "unknown")
        logid = resp.headers.get("X-Tt-Logid", "")
        details = message or api_message
        logid_part = f", logid={logid}" if logid else ""
        return f"火山引擎 ASR 失败: code={status_code}, message={details}{logid_part}"

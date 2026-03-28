from pathlib import Path

import pytest

from app.asr.volcengine import VolcengineASR


class MockResponse:
    def __init__(self, status_code=200, headers=None, json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


class MockAsyncClient:
    def __init__(self, response: MockResponse):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.response


@pytest.mark.asyncio
async def test_volcengine_asr_uses_v3_flash_request(mocker, tmp_path: Path):
    audio_file = tmp_path / "sample.mp3"
    audio_file.write_bytes(b"fake-audio")
    response = MockResponse(
        headers={
            "X-Api-Status-Code": "20000000",
            "X-Api-Message": "OK",
            "X-Tt-Logid": "test-logid",
        },
        json_data={"result": {"text": "识别结果"}},
    )
    client = MockAsyncClient(response)
    mocker.patch("app.asr.volcengine.httpx.AsyncClient", return_value=client)

    asr = VolcengineASR("appid", "token", "volc.bigasr.auc_turbo")
    result = await asr.transcribe(audio_file)

    assert result == "识别结果"
    assert client.calls[0]["url"].endswith("/api/v3/auc/bigmodel/recognize/flash")
    assert client.calls[0]["json"]["audio"]["format"] == "mp3"
    assert client.calls[0]["json"]["audio"]["data"]
    assert client.calls[0]["json"]["request"]["model_name"] == "bigmodel"
    assert client.calls[0]["headers"]["X-Api-App-Key"] == "appid"
    assert client.calls[0]["headers"]["X-Api-Access-Key"] == "token"
    assert client.calls[0]["headers"]["X-Api-Resource-Id"] == "volc.bigasr.auc_turbo"
    assert client.calls[0]["headers"]["X-Api-Sequence"] == "-1"


@pytest.mark.asyncio
async def test_volcengine_asr_surfaces_http_error(mocker, tmp_path: Path):
    audio_file = tmp_path / "sample.mp3"
    audio_file.write_bytes(b"fake-audio")
    response = MockResponse(
        status_code=400,
        headers={"X-Tt-Logid": "bad-request-logid"},
        text='{"message":"bad request"}',
    )
    client = MockAsyncClient(response)
    mocker.patch("app.asr.volcengine.httpx.AsyncClient", return_value=client)

    asr = VolcengineASR("appid", "token", "volc.bigasr.auc_turbo")

    with pytest.raises(RuntimeError, match="HTTP 400"):
        await asr.transcribe(audio_file)

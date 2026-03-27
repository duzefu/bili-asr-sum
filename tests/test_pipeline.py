from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline import run_pipeline
from app.task_manager import TaskManager


@pytest.fixture
def tm() -> TaskManager:
    return TaskManager()


@pytest.fixture
def mock_asr_provider() -> MagicMock:
    provider = MagicMock()
    provider.transcribe = AsyncMock(return_value="识别出的音频文本")
    return provider


class TestPipelineSubtitlePath:
    async def test_completed_with_subtitle_source(self, tm: TaskManager, mocker):
        task = await tm.create("https://example.com/video")
        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch(
            "app.pipeline.download_subtitles",
            return_value=("测试视频标题", "字幕内容文本"),
        )
        mocker.patch("app.pipeline.summarize", return_value="视频总结内容")

        await run_pipeline(task.task_id, task.url)

        result = await tm.get(task.task_id)
        assert result.status == "completed"
        assert result.transcript_source == "subtitle"
        assert result.title == "测试视频标题"
        assert result.summary == "视频总结内容"
        assert result.error is None

    async def test_does_not_call_asr_when_subtitles_available(self, tm: TaskManager, mocker):
        task = await tm.create("https://example.com/video")
        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch(
            "app.pipeline.download_subtitles",
            return_value=("标题", "字幕文本"),
        )
        mocker.patch("app.pipeline.summarize", return_value="总结")
        mock_audio = mocker.patch("app.pipeline.download_audio")
        mock_asr = mocker.patch("app.pipeline.get_asr_provider")

        await run_pipeline(task.task_id, task.url)

        mock_audio.assert_not_called()
        mock_asr.assert_not_called()


class TestPipelineASRPath:
    async def test_completed_with_asr_source(
        self, tm: TaskManager, mocker, tmp_path: Path, mock_asr_provider
    ):
        task = await tm.create("https://example.com/video")
        audio_file = tmp_path / f"{task.task_id}.mp3"
        audio_file.write_bytes(b"fake audio")

        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch("app.pipeline.download_subtitles", return_value=None)
        mocker.patch(
            "app.pipeline.download_audio",
            return_value=(audio_file, "音频视频标题"),
        )
        mocker.patch("app.pipeline.get_asr_provider", return_value=mock_asr_provider)
        mocker.patch("app.pipeline.summarize", return_value="ASR 总结内容")

        await run_pipeline(task.task_id, task.url)

        result = await tm.get(task.task_id)
        assert result.status == "completed"
        assert result.transcript_source == "asr"
        assert result.title == "音频视频标题"
        assert result.summary == "ASR 总结内容"
        mock_asr_provider.transcribe.assert_called_once_with(audio_file)

    async def test_status_transitions_through_transcribing(
        self, tm: TaskManager, mocker, tmp_path: Path, mock_asr_provider
    ):
        task = await tm.create("https://example.com/video")
        audio_file = tmp_path / f"{task.task_id}.mp3"
        audio_file.write_bytes(b"fake audio")

        statuses = []
        original_update = tm.update

        async def capture_update(task_id, **kwargs):
            if "status" in kwargs:
                statuses.append(kwargs["status"])
            await original_update(task_id, **kwargs)

        mocker.patch("app.pipeline.task_manager", tm)
        tm.update = capture_update
        mocker.patch("app.pipeline.download_subtitles", return_value=None)
        mocker.patch(
            "app.pipeline.download_audio",
            return_value=(audio_file, "标题"),
        )
        mocker.patch("app.pipeline.get_asr_provider", return_value=mock_asr_provider)
        mocker.patch("app.pipeline.summarize", return_value="总结")

        await run_pipeline(task.task_id, task.url)

        assert "downloading" in statuses
        assert "transcribing" in statuses
        assert "summarizing" in statuses
        assert "completed" in statuses


class TestPipelineFailurePath:
    async def test_failed_status_on_download_error(self, tm: TaskManager, mocker):
        task = await tm.create("https://example.com/video")
        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch(
            "app.pipeline.download_subtitles",
            side_effect=RuntimeError("下载失败"),
        )

        await run_pipeline(task.task_id, task.url)

        result = await tm.get(task.task_id)
        assert result.status == "failed"
        assert "下载失败" in result.error

    async def test_failed_status_on_asr_error(
        self, tm: TaskManager, mocker, tmp_path: Path
    ):
        task = await tm.create("https://example.com/video")
        audio_file = tmp_path / f"{task.task_id}.mp3"
        audio_file.write_bytes(b"fake audio")

        failing_asr = MagicMock()
        failing_asr.transcribe = AsyncMock(side_effect=RuntimeError("ASR 服务不可用"))

        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch("app.pipeline.download_subtitles", return_value=None)
        mocker.patch(
            "app.pipeline.download_audio",
            return_value=(audio_file, "标题"),
        )
        mocker.patch("app.pipeline.get_asr_provider", return_value=failing_asr)

        await run_pipeline(task.task_id, task.url)

        result = await tm.get(task.task_id)
        assert result.status == "failed"
        assert "ASR 服务不可用" in result.error

    async def test_failed_status_on_summarize_error(self, tm: TaskManager, mocker):
        task = await tm.create("https://example.com/video")
        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch(
            "app.pipeline.download_subtitles",
            return_value=("标题", "字幕文本"),
        )
        mocker.patch(
            "app.pipeline.summarize",
            side_effect=RuntimeError("DeepSeek API 不可用"),
        )

        await run_pipeline(task.task_id, task.url)

        result = await tm.get(task.task_id)
        assert result.status == "failed"
        assert "DeepSeek API 不可用" in result.error

    async def test_temp_files_cleaned_up_on_failure(
        self, tm: TaskManager, mocker, tmp_path: Path
    ):
        task = await tm.create("https://example.com/video")
        leftover = tmp_path / f"{task.task_id}.mp3"
        leftover.write_bytes(b"data")

        mocker.patch("app.pipeline.task_manager", tm)
        mocker.patch(
            "app.pipeline.download_subtitles",
            side_effect=RuntimeError("失败"),
        )
        mocker.patch("app.pipeline.settings")
        import app.pipeline as pipeline_mod
        mocker.patch.object(pipeline_mod.settings, "temp_dir", tmp_path)

        await run_pipeline(task.task_id, task.url)

        assert not leftover.exists()

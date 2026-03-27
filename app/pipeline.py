from app.config import settings
from app.downloader import cleanup_task_files, download_audio, download_subtitles
from app.summarizer import summarize
from app.task_manager import task_manager
from app.asr import get_asr_provider


async def run_pipeline(task_id: str, url: str) -> None:
    """
    视频总结完整流水线：
    1. downloading  - yt-dlp 下载字幕或音频
    2. transcribing - ASR 识别（仅无字幕时）
    3. summarizing  - DeepSeek LLM 生成总结
    4. completed    - 写入结果
    """
    try:
        await task_manager.update(task_id, status="downloading")

        # Step 1: 尝试下载字幕
        subtitle_result = await download_subtitles(url, settings.temp_dir, task_id)

        if subtitle_result is not None:
            title, transcript = subtitle_result
            transcript_source = "subtitle"
            await task_manager.update(
                task_id,
                title=title,
                transcript_source=transcript_source,
            )
        else:
            # Step 2: 下载音频并进行 ASR
            audio_path, title = await download_audio(url, settings.temp_dir, task_id)
            await task_manager.update(task_id, status="transcribing", title=title)

            asr_provider = get_asr_provider(settings)
            transcript = await asr_provider.transcribe(audio_path)
            transcript_source = "asr"
            await task_manager.update(task_id, transcript_source=transcript_source)

        # Step 3: LLM 总结
        await task_manager.update(
            task_id,
            status="summarizing",
            title=title,
            transcript_source=transcript_source,
        )
        summary = await summarize(title, transcript)

        # Step 4: 完成
        await task_manager.update(task_id, status="completed", summary=summary)

    except Exception as exc:
        await task_manager.update(task_id, status="failed", error=str(exc))

    finally:
        cleanup_task_files(task_id, settings.temp_dir)

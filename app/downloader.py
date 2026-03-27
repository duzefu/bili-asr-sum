import asyncio
import re
from pathlib import Path


async def _run_yt_dlp(*args: str) -> tuple[int, str, str]:
    """运行 yt-dlp 子进程，返回 (returncode, stdout, stderr)"""
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def _parse_vtt(content: str) -> str:
    """解析 WebVTT 字幕，提取纯文字并去重"""
    lines = content.splitlines()
    texts = []
    seen = set()
    for line in lines:
        line = line.strip()
        # 跳过 WEBVTT 头、时间戳行、空行、NOTE 行
        if not line or line.startswith("WEBVTT") or "-->" in line or line.startswith("NOTE") or line.isdigit():
            continue
        # 移除 HTML 标签（如 <c>、<00:00:00.000>）
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            texts.append(clean)
    return "\n".join(texts)


def _parse_srt(content: str) -> str:
    """解析 SRT 字幕，提取纯文字并去重"""
    # 移除序号和时间戳行
    content = re.sub(r"^\d+\s*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", "", content)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    seen = set()
    texts = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            texts.append(line)
    return "\n".join(texts)


async def download_subtitles(url: str, output_dir: Path, task_id: str) -> tuple[str, str] | None:
    """
    尝试下载字幕（自动字幕优先）。
    返回 (标题, 字幕文本) 或 None（无字幕时）。
    语言优先级：zh-Hans > zh > en
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"{task_id}_sub")

    # 先获取视频标题
    rc, stdout, _ = await _run_yt_dlp("--get-title", "--no-playlist", url)
    title = stdout.strip().splitlines()[0] if rc == 0 and stdout.strip() else "未知标题"

    # 尝试下载自动字幕
    for lang in ["zh-Hans", "zh", "en"]:
        rc, _, _ = await _run_yt_dlp(
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", lang,
            "--skip-download",
            "--no-playlist",
            "-o", output_template,
            url,
        )
        # 查找生成的字幕文件
        for ext in [".vtt", ".srt"]:
            sub_files = list(output_dir.glob(f"{task_id}_sub*.{lang}{ext}")) + \
                        list(output_dir.glob(f"{task_id}_sub*{ext}"))
            if sub_files:
                sub_file = sub_files[0]
                content = sub_file.read_text(encoding="utf-8", errors="replace")
                sub_file.unlink(missing_ok=True)
                if ext == ".vtt":
                    text = _parse_vtt(content)
                else:
                    text = _parse_srt(content)
                if text.strip():
                    return title, text

    return None


async def download_audio(url: str, output_dir: Path, task_id: str) -> tuple[Path, str]:
    """
    下载视频音频为 mp3 格式（16kHz，满足火山引擎 ASR 要求）。
    返回 (音频文件路径, 视频标题)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"{task_id}.%(ext)s")

    # 先获取标题
    rc, stdout, _ = await _run_yt_dlp("--get-title", "--no-playlist", url)
    title = stdout.strip().splitlines()[0] if rc == 0 and stdout.strip() else "未知标题"

    rc, stdout, stderr = await _run_yt_dlp(
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--postprocessor-args", "ffmpeg:-ar 16000",
        "--no-playlist",
        "-o", output_template,
        url,
    )

    if rc != 0:
        raise RuntimeError(f"yt-dlp 音频下载失败: {stderr[-500:]}")

    # 找到生成的音频文件
    audio_files = list(output_dir.glob(f"{task_id}.mp3"))
    if not audio_files:
        # fallback：查找任意生成的音频文件
        audio_files = list(output_dir.glob(f"{task_id}.*"))
    if not audio_files:
        raise RuntimeError("yt-dlp 下载完成但未找到音频文件")

    return audio_files[0], title


def cleanup_task_files(task_id: str, output_dir: Path) -> None:
    """清理任务相关的临时文件"""
    for f in output_dir.glob(f"{task_id}*"):
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass

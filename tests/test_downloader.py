from pathlib import Path

import pytest

from app.downloader import _parse_vtt, _parse_srt, cleanup_task_files


# ── _parse_vtt ──────────────────────────────────────────────────────────────

class TestParseVtt:
    def test_extracts_text_from_valid_vtt(self):
        vtt = """\
WEBVTT
Kind: captions
Language: zh-Hans

00:00:01.000 --> 00:00:03.000
这是第一句话

00:00:03.500 --> 00:00:05.000
这是第二句话
"""
        result = _parse_vtt(vtt)
        assert "这是第一句话" in result
        assert "这是第二句话" in result

    def test_removes_html_tags(self):
        vtt = """\
WEBVTT

00:00:01.000 --> 00:00:03.000
<c>带有标签的</c>文字<00:00:01.500><c>内容</c>
"""
        result = _parse_vtt(vtt)
        assert "<c>" not in result
        assert "带有标签的" in result
        assert "文字" in result

    def test_deduplicates_repeated_lines(self):
        vtt = """\
WEBVTT

00:00:01.000 --> 00:00:03.000
重复的句子

00:00:02.000 --> 00:00:04.000
重复的句子

00:00:04.000 --> 00:00:06.000
不重复的句子
"""
        result = _parse_vtt(vtt)
        lines = result.splitlines()
        assert lines.count("重复的句子") == 1
        assert "不重复的句子" in result

    def test_skips_webvtt_header(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n正文\n"
        result = _parse_vtt(vtt)
        assert "WEBVTT" not in result
        assert "正文" in result

    def test_skips_timestamp_lines(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n句子\n"
        result = _parse_vtt(vtt)
        assert "-->" not in result

    def test_empty_content_returns_empty_string(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n   \n"
        result = _parse_vtt(vtt)
        assert result.strip() == ""

    def test_skips_note_lines(self):
        vtt = "WEBVTT\n\nNOTE This is a comment\n\n00:00:01.000 --> 00:00:02.000\n正文\n"
        result = _parse_vtt(vtt)
        assert "NOTE" not in result
        assert "正文" in result


# ── _parse_srt ──────────────────────────────────────────────────────────────

class TestParseSrt:
    def test_extracts_text_from_valid_srt(self):
        srt = """\
1
00:00:01,000 --> 00:00:03,000
第一行字幕

2
00:00:03,500 --> 00:00:05,000
第二行字幕
"""
        result = _parse_srt(srt)
        assert "第一行字幕" in result
        assert "第二行字幕" in result

    def test_removes_sequence_numbers(self):
        srt = "1\n00:00:01,000 --> 00:00:03,000\n句子\n"
        result = _parse_srt(srt)
        lines = result.splitlines()
        assert "1" not in lines

    def test_removes_timestamp_lines(self):
        srt = "1\n00:00:01,000 --> 00:00:03,000\n句子\n"
        result = _parse_srt(srt)
        assert "-->" not in result

    def test_deduplicates_repeated_lines(self):
        srt = """\
1
00:00:01,000 --> 00:00:03,000
重复句子

2
00:00:02,000 --> 00:00:04,000
重复句子

3
00:00:04,000 --> 00:00:06,000
唯一句子
"""
        result = _parse_srt(srt)
        lines = result.splitlines()
        assert lines.count("重复句子") == 1
        assert "唯一句子" in result


# ── cleanup_task_files ───────────────────────────────────────────────────────

class TestCleanupTaskFiles:
    def test_deletes_files_with_task_id_prefix(self, tmp_dir: Path):
        task_id = "abc123"
        files = [
            tmp_dir / f"{task_id}.mp3",
            tmp_dir / f"{task_id}_sub.zh-Hans.vtt",
            tmp_dir / f"{task_id}_extra.txt",
        ]
        for f in files:
            f.write_text("data")

        cleanup_task_files(task_id, tmp_dir)

        for f in files:
            assert not f.exists()

    def test_does_not_delete_other_task_files(self, tmp_dir: Path):
        task_id = "abc123"
        other_file = tmp_dir / "xyz999.mp3"
        other_file.write_text("other")
        (tmp_dir / f"{task_id}.mp3").write_text("mine")

        cleanup_task_files(task_id, tmp_dir)

        assert other_file.exists()

    def test_no_error_when_no_matching_files(self, tmp_dir: Path):
        # 不应抛出任何异常
        cleanup_task_files("nonexistent-task", tmp_dir)

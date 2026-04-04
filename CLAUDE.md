# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Bilibili / YouTube 视频内容总结服务。提交视频 URL，服务自动下载字幕或音频，经 ASR 转文字后由 DeepSeek LLM 生成结构化摘要，通过 REST API 异步返回结果。

## 常用命令

```bash
# 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行全部测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_api.py -v

# 运行单个测试函数
pytest tests/test_api.py::test_submit_summarize -v
```

## 架构概述

### 处理流水线

所有视频处理通过 `app/pipeline.py` 的 `run_pipeline()` 异步执行，状态流转：

```
pending → downloading → [transcribing] → summarizing → completed / failed
```

- **缓存命中**：直接返回，跳过下载/ASR/LLM 全流程
- **有字幕**：`downloading` 后直接进入 `summarizing`
- **无字幕**：`downloading` → `transcribing`（ASR）→ `summarizing`

### 关键模块

| 模块 | 职责 |
|---|---|
| `app/main.py` | FastAPI 路由、CORS、前端静态文件挂载、lifespan 初始化缓存 |
| `app/pipeline.py` | 流水线编排，组合 downloader / ASR / summarizer / cache |
| `app/task_manager.py` | 内存任务注册表，任务状态读写（重启后丢失） |
| `app/downloader.py` | yt-dlp 封装，下载字幕或音频，带指数退避重试 |
| `app/summarizer.py` | 调用 DeepSeek API 生成总结 |
| `app/config.py` | pydantic-settings，从 `.env` 读取配置，单例 `settings` |

### ASR 模块（`app/asr/`）

通过 `get_asr_provider(settings)` 工厂函数获取实现：
- `aliyun.py`：阿里云 DashScope FunASR（paraformer-v2），结果通过二次 HTTP 请求获取
- `volcengine.py`：火山引擎豆包 ASR，要求 16kHz 音频，单文件 ≤ 2h/100MB
- `local_sensevoice.py`：离线 SenseVoice-Small，首次运行自动从 ModelScope 下载约 500MB 模型

新增 ASR 后端：继承 `app/asr/base.py` 中的 `ASRProvider` 抽象类，实现 `async def transcribe(audio_path: Path) -> str`，然后在 `app/asr/__init__.py` 的 `get_asr_provider()` 中注册。

### 缓存模块（`app/cache/`）

通过 `get_content_cache(settings)` 工厂函数在 lifespan 初始化：
- `memory.py`：内存缓存，进程内有效
- `upstash.py`：Upstash Redis REST，跨实例共享

URL 规范化逻辑在 `app/cache/base.py` 的 `normalize_url_to_key()`，同一视频的不同 URL 变体映射到同一缓存 key。

新增缓存后端：继承 `ContentCache` 抽象类，实现 `get / set / close` 三个方法。

### 前端与油猴脚本

- `frontend/`：简单 HTML+CSS 前端，由 FastAPI 挂载为静态文件，通过 `/` 访问
- `extension/bili-asr-sum.user.js`：油猴脚本，在 Bilibili/YouTube 缩略图旁注入总结按钮，通过侧边栏展示结果

## 配置

复制 `.env.example` 为 `.env` 并填写：

- `ASR_PROVIDER`：`aliyun` / `volcengine` / `local_sensevoice`
- `DEEPSEEK_API_KEY`：必填
- `CACHE_BACKEND`：`memory`（默认）或 `upstash`

## 测试

测试使用 `pytest-asyncio`（`asyncio_mode = auto`）和 `pytest-mock`。`conftest.py` 提供：
- `task_manager` fixture：每个测试独立实例，避免全局状态污染
- `client` fixture：基于 `httpx.AsyncClient` + `ASGITransport` 的 FastAPI 测试客户端

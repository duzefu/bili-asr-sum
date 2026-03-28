# 🎬 bili-asr-sum
# 🎬 bili-asr-sum

Bilibili / YouTube 视频内容总结服务。提交视频链接，自动下载字幕或音频，经 ASR 转文字后由 DeepSeek LLM 生成结构化总结，通过 REST API 异步返回结果。
Bilibili / YouTube video content summarization service. Submit a video link to automatically download subtitles or audio, transcribe via ASR, generate structured summaries using DeepSeek LLM, and return results asynchronously via REST API.

## ✨ 功能
## ✨ Features

- 🎥 支持 Bilibili 和 YouTube 视频链接
- 🎥 Supports Bilibili and YouTube video links
- 📝 优先使用视频自带字幕，无字幕时自动下载音频并进行 ASR
- 📝 Prioritizes video's built-in subtitles; automatically downloads audio and performs ASR when no subtitles are available
- 🎙️ 支持两个 ASR 后端，可通过配置切换：
- 🎙️ Supports two ASR backends, switchable via configuration:
  - **阿里云 DashScope FunASR**（`paraformer-v2`）
  - **Alibaba Cloud DashScope FunASR** (`paraformer-v2`)
  - **火山引擎豆包语音识别**（大模型录音文件极速版）
  - **Volcengine Doubao Speech Recognition** (Large Model Recording Express Edition)
- 🤖 使用 DeepSeek API 生成中文总结（核心主题 / 主要内容 / 关键结论）
- 🤖 Uses DeepSeek API to generate Chinese summaries (core topics / main content / key conclusions)
- ⏳ 异步处理 + 轮询状态，适合长视频场景
- ⏳ Asynchronous processing + status polling, suitable for long video scenarios
- 💾 支持内容缓存，避免重复处理同一视频：
- 💾 Supports content caching to avoid reprocessing the same video:
  - **内存缓存**：默认，适合单机部署
  - **Memory Cache**: Default, suitable for single-instance deployment
  - **Upstash Redis**：云端 Redis，支持多实例共享缓存
  - **Upstash Redis**: Cloud Redis, supports multi-instance shared cache

## 🔄 处理流程
## 🔄 Processing Flow

```
提交 URL
Submit URL
  └─ downloading  ── 尝试下载字幕
  └─ downloading  ── Try to download subtitles
       ├─ 有字幕 ──────────────────────── summarizing ── completed
       ├─ Has subtitles ──────────────────────── summarizing ── completed
       └─ 无字幕 ── transcribing（ASR） ── summarizing ── completed
       └─ No subtitles ── transcribing（ASR） ── summarizing ── completed
                                                          failed（任意步骤出错）
                                                          failed (error at any step)
```

## 🚀 快速开始
## 🚀 Quick Start

### 依赖
### Dependencies

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html)（音频转换必须）
- [ffmpeg](https://ffmpeg.org/download.html) (required for audio conversion)

### 安装
### Installation

```bash
git clone <repo-url>
cd bili-asr-sum
pip install -r requirements.txt
```

### 配置
### Configuration

```bash
cp .env.example .env
```

编辑 `.env`，填入以下内容：
Edit `.env` and fill in the following:

| 变量 | 必须 | 说明 |
| Variable | Required | Description |
|---|---|---|
| `ASR_PROVIDER` | 是 | `aliyun` 或 `volcengine` |
| `ASR_PROVIDER` | Yes | `aliyun` or `volcengine` |
| `ALIYUN_DASHSCOPE_API_KEY` | aliyun 时必须 | 阿里云 DashScope API Key |
| `ALIYUN_DASHSCOPE_API_KEY` | Required for aliyun | Alibaba Cloud DashScope API Key |
| `VOLCENGINE_APP_ID` | volcengine 时必须 | 火山引擎 App ID |
| `VOLCENGINE_APP_ID` | Required for volcengine | Volcengine App ID |
| `VOLCENGINE_ACCESS_TOKEN` | volcengine 时必须 | 火山引擎 Access Token |
| `VOLCENGINE_ACCESS_TOKEN` | Required for volcengine | Volcengine Access Token |
| `VOLCENGINE_RESOURCE_ID` | 否 | 火山引擎资源 ID，默认 `volc.bigasr.auc_turbo` |
| `VOLCENGINE_RESOURCE_ID` | No | Volcengine Resource ID, default `volc.bigasr.auc_turbo` |
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key |
| `DEEPSEEK_API_KEY` | Yes | DeepSeek API Key |
| `CACHE_BACKEND` | 否 | 缓存后端：`memory`（默认）或 `upstash` |
| `CACHE_BACKEND` | No | Cache backend: `memory` (default) or `upstash` |
| `CACHE_TTL_SECONDS` | 否 | 缓存过期时间（秒），默认 30 天 |
| `CACHE_TTL_SECONDS` | No | Cache TTL in seconds, default 30 days |
| `CACHE_STORE_TRANSCRIPT` | 否 | 是否缓存原文，默认 `false` |
| `CACHE_STORE_TRANSCRIPT` | No | Whether to cache transcript, default `false` |
| `UPSTASH_REDIS_REST_URL` | upstash 时必须 | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_URL` | Required for upstash | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | upstash 时必须 | Upstash Redis REST Token |
| `UPSTASH_REDIS_REST_TOKEN` | Required for upstash | Upstash Redis REST Token |

### 启动
### Start

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📖 API

### POST /api/summarize

提交视频处理任务，立即返回 `task_id`，后台异步处理。
Submit a video processing task, immediately returns a `task_id`, processed asynchronously in the background.

**请求**
**Request**

```bash
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bilibili.com/video/BV1xx"}'
```

**响应** `202`
**Response** `202`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### GET /api/tasks/{task_id}

轮询任务状态和结果。
Poll task status and results.

```bash
curl http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000
```

**响应** `200`
**Response** `200`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://www.bilibili.com/video/BV1xx",
  "title": "视频标题",
  "title": "Video Title",
  "transcript_source": "subtitle",
  "summary": "1. **核心主题**：...\n2. **主要内容**：...\n3. **关键结论**：...",
  "summary": "1. **Core Topics**: ...\n2. **Main Content**: ...\n3. **Key Conclusions**: ...",
  "error": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:01:30Z"
}
```

**status 取值**
**Status Values**

| 值 | 含义 |
| Value | Meaning |
|---|---|
| `pending` | 等待处理 |
| `pending` | Waiting for processing |
| `downloading` | 下载字幕或音频 |
| `downloading` | Downloading subtitles or audio |
| `transcribing` | ASR 语音识别 |
| `transcribing` | ASR speech recognition |
| `summarizing` | LLM 生成总结 |
| `summarizing` | LLM generating summary |
| `completed` | 处理完成 |
| `completed` | Processing completed |
| `failed` | 处理失败，见 `error` 字段 |
| `failed` | Processing failed, see `error` field |

### GET /health

健康检查，返回当前配置的缓存后端信息。
Health check, returns current cache backend configuration info.

```bash
curl http://localhost:8000/health
# {"status": "ok", "asr_provider": "aliyun", "cache_backend": "memory"}
```

### 交互式文档
### Interactive Documentation

服务启动后访问 `http://localhost:8000/docs` 查看 Swagger UI。
After starting the service, visit `http://localhost:8000/docs` to view Swagger UI.

## 🛠️ 开发
## 🛠️ Development

### 运行测试
### Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### 项目结构
### Project Structure

```
app/
├── main.py           # FastAPI 应用与路由
├── main.py           # FastAPI application and routes
├── config.py         # 环境变量配置（pydantic-settings）
├── config.py         # Environment variable configuration (pydantic-settings)
├── models.py         # 请求/响应 Pydantic 模型
├── models.py         # Request/Response Pydantic models
├── task_manager.py   # 内存任务注册表
├── task_manager.py   # In-memory task registry
├── pipeline.py       # 处理流水线编排
├── pipeline.py       # Processing pipeline orchestration
├── downloader.py     # yt-dlp 封装（字幕 / 音频下载）
├── downloader.py     # yt-dlp wrapper (subtitle/audio download)
├── summarizer.py     # DeepSeek API 调用
├── summarizer.py     # DeepSeek API calls
└── asr/
    ├── base.py       # ASRProvider 抽象基类
    ├── base.py       # ASRProvider abstract base class
    ├── aliyun.py     # 阿里云 DashScope FunASR
    ├── aliyun.py     # Alibaba Cloud DashScope FunASR
    └── volcengine.py # 火山引擎豆包 ASR
    └── volcengine.py # Volcengine Doubao ASR
tests/
├── conftest.py
├── test_downloader.py
├── test_task_manager.py
├── test_api.py
└── test_pipeline.py
```

## 📁 项目结构
## 📁 Project Structure

```
app/
├── main.py           # FastAPI 应用与路由
├── main.py           # FastAPI application and routes
├── config.py         # 环境变量配置（pydantic-settings）
├── config.py         # Environment variable configuration (pydantic-settings)
├── models.py         # 请求/响应 Pydantic 模型
├── models.py         # Request/Response Pydantic models
├── task_manager.py   # 内存任务注册表
├── task_manager.py   # In-memory task registry
├── pipeline.py       # 处理流水线编排
├── pipeline.py       # Processing pipeline orchestration
├── downloader.py     # yt-dlp 封装（字幕 / 音频下载）
├── downloader.py     # yt-dlp wrapper (subtitle/audio download)
├── summarizer.py     # DeepSeek API 调用
├── summarizer.py     # DeepSeek API calls
├── cache/            # 缓存模块
├── cache/            # Cache module
│   ├── base.py       # 缓存抽象基类
│   ├── base.py       # Cache abstract base class
│   ├── memory.py     # 内存缓存实现
│   ├── memory.py     # In-memory cache implementation
│   └── upstash.py    # Upstash Redis 实现
│   └── upstash.py    # Upstash Redis implementation
└── asr/
    ├── base.py       # ASRProvider 抽象基类
    ├── base.py       # ASRProvider abstract base class
    ├── aliyun.py     # 阿里云 DashScope FunASR
    ├── aliyun.py     # Alibaba Cloud DashScope FunASR
    └── volcengine.py # 火山引擎豆包 ASR
    └── volcengine.py # Volcengine Doubao ASR
tests/
├── conftest.py
├── test_downloader.py
├── test_task_manager.py
├── test_api.py
└── test_pipeline.py
```

## ⚠️ 注意事项
## ⚠️ Notes

- 🧹 临时音频文件在处理完成后自动删除
- 🧹 Temporary audio files are automatically deleted after processing
- 💾 任务状态存储在内存中，重启服务后会丢失（已完成的视频结果可通过缓存恢复）
- 💾 Task status is stored in memory and will be lost after service restart (completed video results can be recovered via cache)
- 🔊 火山引擎 ASR 当前接入的是大模型录音文件极速版，要求音频采样率为 16kHz，且单文件不超过 2 小时、100MB
- 🔊 Volcengine ASR currently uses the Large Model Recording Express Edition, requiring 16kHz audio sample rate, with single files not exceeding 2 hours or 100MB
- ☁️ 阿里云 FunASR 识别结果通过二次 HTTP 请求获取（`transcription_url`）
- ☁️ Alibaba Cloud FunASR recognition results are retrieved via a secondary HTTP request (`transcription_url`)
- 🌐 使用 Upstash 缓存时，已处理视频的结果会在 TTL 期内跨实例共享，避免重复消耗 ASR/LLM 资源
- 🌐 When using Upstash cache, processed video results are shared across instances within TTL, avoiding redundant ASR/LLM resource consumption

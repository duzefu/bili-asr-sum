# 🎬 bili-asr-sum

[中文](README.md) | English

Bilibili / YouTube video content summarization service. Submit a video link to automatically download subtitles or audio, transcribe via ASR, generate structured summaries using DeepSeek LLM, and return results asynchronously via REST API.

## ✨ Features

- 🎥 Supports Bilibili and YouTube video links
- 📝 Prioritizes video's built-in subtitles; automatically downloads audio and performs ASR when no subtitles are available
- 🎙️ Supports three ASR backends, switchable via configuration:
  - **Alibaba Cloud DashScope FunASR** (`paraformer-v2`)
  - **Volcengine Doubao Speech Recognition** (Large Model Recording Express Edition)
  - **Local SenseVoice-Small** (offline, no API key required, Apache 2.0)
- 🤖 Uses DeepSeek API to generate Chinese summaries (core topics / main content / key conclusions)
- ⏳ Asynchronous processing + status polling, suitable for long video scenarios
- 💾 Supports content caching to avoid reprocessing the same video:
  - **Memory Cache**: Default, suitable for single-instance deployment
  - **Upstash Redis**: Cloud Redis, supports multi-instance shared cache

## 🔄 Processing Flow

```
Submit URL
  └─ downloading  ── Try to download subtitles
       ├─ Has subtitles ──────────────────────── summarizing ── completed
       └─ No subtitles ── transcribing（ASR） ── summarizing ── completed
                                                          failed (error at any step)
```

## 🚀 Quick Start

### Dependencies

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html) (required for audio conversion)

### Installation

```bash
git clone <repo-url>
cd bili-asr-sum
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` and fill in the following:

| Variable | Required | Description |
|---|---|---|
| `ASR_PROVIDER` | Yes | `aliyun`, `volcengine`, or `local_sensevoice` |
| `ALIYUN_DASHSCOPE_API_KEY` | Required for aliyun | Alibaba Cloud DashScope API Key |
| `VOLCENGINE_APP_ID` | Required for volcengine | Volcengine App ID |
| `VOLCENGINE_ACCESS_TOKEN` | Required for volcengine | Volcengine Access Token |
| `VOLCENGINE_RESOURCE_ID` | No | Volcengine Resource ID, default `volc.bigasr.auc_turbo` |
| `LOCAL_ASR_DEVICE` | No | Local ASR inference device, default `cpu` (e.g. `cuda:0`, `mps`) |
| `LOCAL_ASR_LANGUAGE` | No | Local ASR language, default `auto` (e.g. `zh`, `en`) |
| `DEEPSEEK_API_KEY` | Yes | DeepSeek API Key |
| `CACHE_BACKEND` | No | Cache backend: `memory` (default) or `upstash` |
| `CACHE_TTL_SECONDS` | No | Cache TTL in seconds, default 30 days |
| `CACHE_STORE_TRANSCRIPT` | No | Whether to cache transcript, default `false` |
| `UPSTASH_REDIS_REST_URL` | Required for upstash | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | Required for upstash | Upstash Redis REST Token |

### Start

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📖 API

### POST /api/summarize

Submit a video processing task, immediately returns a `task_id`, processed asynchronously in the background.

**Request**

```bash
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bilibili.com/video/BV1xx"}'
```

**Response** `202`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### GET /api/tasks/{task_id}

Poll task status and results.

```bash
curl http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000
```

**Response** `200`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://www.bilibili.com/video/BV1xx",
  "title": "Video Title",
  "transcript_source": "subtitle",
  "summary": "1. **Core Topics**: ...\n2. **Main Content**: ...\n3. **Key Conclusions**: ...",
  "error": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:01:30Z"
}
```

**Status Values**

| Value | Meaning |
|---|---|
| `pending` | Waiting for processing |
| `downloading` | Downloading subtitles or audio |
| `transcribing` | ASR speech recognition |
| `summarizing` | LLM generating summary |
| `completed` | Processing completed |
| `failed` | Processing failed, see `error` field |

### GET /health

Health check, returns current cache backend configuration info.

```bash
curl http://localhost:8000/health
# {"status": "ok", "asr_provider": "aliyun", "cache_backend": "memory"}
```

### Interactive Documentation

After starting the service, visit `http://localhost:8000/docs` to view Swagger UI.

## 🧩 Userscript

A browser userscript is provided that adds a summary button next to YouTube and Bilibili video thumbnails for one-click video content summarization.

### Features

- 🖱️ Summary button appears when hovering over video thumbnails
- 📝 Click the button to submit the video for summarization
- 📊 Sidebar displays processing progress and results in real-time
- 🎨 Auto-adapts to YouTube / Bilibili dark mode
- ⚙️ Configure API service address via userscript menu

### Installation

1. Install browser extension [Tampermonkey](https://www.tampermonkey.net/)
2. Open script file [`extension/bili-asr-sum.user.js`](extension/bili-asr-sum.user.js)
3. Click Tampermonkey extension icon, select "Add new script"
4. Copy and paste script content and save

### Usage

1. Visit YouTube or Bilibili website
2. Click "⚙️ 设置 API 地址" in Tampermonkey extension menu
3. Enter your deployed API service address (e.g., `https://api.example.com`)
4. Hover over any video thumbnail, click the 📝 button in the top-right corner
5. Sidebar will automatically pop up, showing processing progress and summary results

## 🛠️ Development

### Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Project Structure

```
app/
├── main.py           # FastAPI application and routes
├── config.py         # Environment variable configuration (pydantic-settings)
├── models.py         # Request/Response Pydantic models
├── task_manager.py   # In-memory task registry
├── pipeline.py       # Processing pipeline orchestration
├── downloader.py     # yt-dlp wrapper (subtitle/audio download)
├── summarizer.py     # DeepSeek API calls
├── cache/            # Cache module
│   ├── base.py       # Cache abstract base class
│   ├── memory.py     # In-memory cache implementation
│   └── upstash.py    # Upstash Redis implementation
└── asr/
    ├── base.py             # ASRProvider abstract base class
    ├── aliyun.py           # Alibaba Cloud DashScope FunASR
    ├── volcengine.py       # Volcengine Doubao ASR
    └── local_sensevoice.py # Local SenseVoice offline ASR
tests/
├── conftest.py
├── test_downloader.py
├── test_task_manager.py
├── test_api.py
└── test_pipeline.py
```

## ⚠️ Notes

- 🧹 Temporary audio files are automatically deleted after processing
- 💾 Task status is stored in memory and will be lost after service restart (completed video results can be recovered via cache)
- 🔊 Volcengine ASR currently uses the Large Model Recording Express Edition, requiring 16kHz audio sample rate, with single files not exceeding 2 hours or 100MB
- ☁️ Alibaba Cloud FunASR recognition results are retrieved via a secondary HTTP request (`transcription_url`)
- 🖥️ Local SenseVoice automatically downloads the model from ModelScope on first run (~500MB); requires `pip install funasr modelscope torch torchaudio`
- 🌐 When using Upstash cache, processed video results are shared across instances within TTL, avoiding redundant ASR/LLM resource consumption
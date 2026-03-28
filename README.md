# 🎬 bili-asr-sum

Bilibili / YouTube 视频内容总结服务。提交视频链接，自动下载字幕或音频，经 ASR 转文字后由 DeepSeek LLM 生成结构化总结，通过 REST API 异步返回结果。

## ✨ 功能

- 🎥 支持 Bilibili 和 YouTube 视频链接
- 📝 优先使用视频自带字幕，无字幕时自动下载音频并进行 ASR
- 🎙️ 支持两个 ASR 后端，可通过配置切换：
  - **阿里云 DashScope FunASR**（`paraformer-v2`）
  - **火山引擎豆包语音识别**（大模型录音文件极速版）
- 🤖 使用 DeepSeek API 生成中文总结（核心主题 / 主要内容 / 关键结论）
- ⏳ 异步处理 + 轮询状态，适合长视频场景
- 💾 支持内容缓存，避免重复处理同一视频：
  - **内存缓存**：默认，适合单机部署
  - **Upstash Redis**：云端 Redis，支持多实例共享缓存

## 🔄 处理流程

```
提交 URL
  └─ downloading  ── 尝试下载字幕
       ├─ 有字幕 ──────────────────────── summarizing ── completed
       └─ 无字幕 ── transcribing（ASR） ── summarizing ── completed
                                                          failed（任意步骤出错）
```

## 🚀 快速开始

### 依赖

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html)（音频转换必须）

### 安装

```bash
git clone <repo-url>
cd bili-asr-sum
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
```

编辑 `.env`，填入以下内容：

| 变量 | 必须 | 说明 |
|---|---|---|
| `ASR_PROVIDER` | 是 | `aliyun` 或 `volcengine` |
| `ALIYUN_DASHSCOPE_API_KEY` | aliyun 时必须 | 阿里云 DashScope API Key |
| `VOLCENGINE_APP_ID` | volcengine 时必须 | 火山引擎 App ID |
| `VOLCENGINE_ACCESS_TOKEN` | volcengine 时必须 | 火山引擎 Access Token |
| `VOLCENGINE_RESOURCE_ID` | 否 | 火山引擎资源 ID，默认 `volc.bigasr.auc_turbo` |
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key |
| `CACHE_BACKEND` | 否 | 缓存后端：`memory`（默认）或 `upstash` |
| `CACHE_TTL_SECONDS` | 否 | 缓存过期时间（秒），默认 30 天 |
| `CACHE_STORE_TRANSCRIPT` | 否 | 是否缓存原文，默认 `false` |
| `UPSTASH_REDIS_REST_URL` | upstash 时必须 | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | upstash 时必须 | Upstash Redis REST Token |

### 启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📖 API

### POST /api/summarize

提交视频处理任务，立即返回 `task_id`，后台异步处理。

**请求**

```bash
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bilibili.com/video/BV1xx"}'
```

**响应** `202`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### GET /api/tasks/{task_id}

轮询任务状态和结果。

```bash
curl http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000
```

**响应** `200`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://www.bilibili.com/video/BV1xx",
  "title": "视频标题",
  "transcript_source": "subtitle",
  "summary": "1. **核心主题**：...\n2. **主要内容**：...\n3. **关键结论**：...",
  "error": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:01:30Z"
}
```

**status 取值**

| 值 | 含义 |
|---|---|
| `pending` | 等待处理 |
| `downloading` | 下载字幕或音频 |
| `transcribing` | ASR 语音识别 |
| `summarizing` | LLM 生成总结 |
| `completed` | 处理完成 |
| `failed` | 处理失败，见 `error` 字段 |

### GET /health

健康检查，返回当前配置的缓存后端信息。

```bash
curl http://localhost:8000/health
# {"status": "ok", "asr_provider": "aliyun", "cache_backend": "memory"}
```

### 交互式文档

服务启动后访问 `http://localhost:8000/docs` 查看 Swagger UI。

## 🛠️ 开发

### 运行测试

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### 项目结构

```
app/
├── main.py           # FastAPI 应用与路由
├── config.py         # 环境变量配置（pydantic-settings）
├── models.py         # 请求/响应 Pydantic 模型
├── task_manager.py   # 内存任务注册表
├── pipeline.py       # 处理流水线编排
├── downloader.py     # yt-dlp 封装（字幕 / 音频下载）
├── summarizer.py     # DeepSeek API 调用
└── asr/
    ├── base.py       # ASRProvider 抽象基类
    ├── aliyun.py     # 阿里云 DashScope FunASR
    └── volcengine.py # 火山引擎豆包 ASR
tests/
├── conftest.py
├── test_downloader.py
├── test_task_manager.py
├── test_api.py
└── test_pipeline.py
```

## 📁 项目结构

```
app/
├── main.py           # FastAPI 应用与路由
├── config.py         # 环境变量配置（pydantic-settings）
├── models.py         # 请求/响应 Pydantic 模型
├── task_manager.py   # 内存任务注册表
├── pipeline.py       # 处理流水线编排
├── downloader.py     # yt-dlp 封装（字幕 / 音频下载）
├── summarizer.py     # DeepSeek API 调用
├── cache/            # 缓存模块
│   ├── base.py       # 缓存抽象基类
│   ├── memory.py     # 内存缓存实现
│   └── upstash.py    # Upstash Redis 实现
└── asr/
    ├── base.py       # ASRProvider 抽象基类
    ├── aliyun.py     # 阿里云 DashScope FunASR
    └── volcengine.py # 火山引擎豆包 ASR
tests/
├── conftest.py
├── test_downloader.py
├── test_task_manager.py
├── test_api.py
└── test_pipeline.py
```

## ⚠️ 注意事项

- 🧹 临时音频文件在处理完成后自动删除
- 💾 任务状态存储在内存中，重启服务后会丢失（已完成的视频结果可通过缓存恢复）
- 🔊 火山引擎 ASR 当前接入的是大模型录音文件极速版，要求音频采样率为 16kHz，且单文件不超过 2 小时、100MB
- ☁️ 阿里云 FunASR 识别结果通过二次 HTTP 请求获取（`transcription_url`）
- 🌐 使用 Upstash 缓存时，已处理视频的结果会在 TTL 期内跨实例共享，避免重复消耗 ASR/LLM 资源

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import app.cache as cache_module
from app.cache import get_content_cache
from app.config import settings
from app.models import SummarizeRequest, SubmitResponse, TaskResponse
from app.pipeline import run_pipeline
from app.task_manager import task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保临时目录存在
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    # 初始化内容缓存后端
    cache_module.content_cache = get_content_cache(settings)
    yield
    # 关闭缓存（释放 HTTP 连接池等资源）
    if cache_module.content_cache is not None:
        await cache_module.content_cache.close()


app = FastAPI(
    title="bili-asr-sum",
    description="Bilibili / YouTube 视频内容总结服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend_dir / "index.html"))


@app.post(
    "/api/summarize",
    response_model=SubmitResponse,
    status_code=202,
    summary="提交视频总结任务",
)
async def submit_summarize(request: SummarizeRequest, background_tasks: BackgroundTasks):
    """
    接受 Bilibili 或 YouTube 视频链接，异步处理并返回 task_id。
    通过 GET /api/tasks/{task_id} 轮询获取结果。
    """
    task = await task_manager.create(request.url)
    background_tasks.add_task(run_pipeline, task.task_id, request.url)
    return SubmitResponse(task_id=task.task_id, status=task.status)


@app.get(
    "/api/tasks/{task_id}",
    response_model=TaskResponse,
    summary="查询任务状态",
)
async def get_task(task_id: str):
    """
    查询任务处理状态和结果。
    status 取值：pending | downloading | transcribing | summarizing | completed | failed
    """
    task = await task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        url=task.url,
        title=task.title,
        transcript_source=task.transcript_source,
        summary=task.summary,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "ok", "asr_provider": settings.asr_provider}

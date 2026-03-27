import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.task_manager import TaskManager


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def task_manager() -> TaskManager:
    """每个测试使用独立的 TaskManager 实例，不污染全局状态"""
    return TaskManager()


@pytest.fixture
async def client():
    """FastAPI 异步测试客户端"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

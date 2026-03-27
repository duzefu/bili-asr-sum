import asyncio
import uuid

import pytest

from app.task_manager import TaskManager


@pytest.fixture
def tm() -> TaskManager:
    return TaskManager()


class TestTaskManagerCreate:
    async def test_returns_task_record_with_pending_status(self, tm: TaskManager):
        task = await tm.create("https://example.com/video")
        assert task.status == "pending"

    async def test_returns_task_record_with_given_url(self, tm: TaskManager):
        url = "https://www.bilibili.com/video/BV1xx"
        task = await tm.create(url)
        assert task.url == url

    async def test_task_id_is_valid_uuid(self, tm: TaskManager):
        task = await tm.create("https://example.com")
        uuid.UUID(task.task_id)  # 不抛出异常即为合法 UUID

    async def test_each_task_gets_unique_id(self, tm: TaskManager):
        task1 = await tm.create("https://example.com/1")
        task2 = await tm.create("https://example.com/2")
        assert task1.task_id != task2.task_id

    async def test_concurrent_creates_have_no_id_collision(self, tm: TaskManager):
        tasks = await asyncio.gather(*[tm.create(f"https://example.com/{i}") for i in range(50)])
        ids = [t.task_id for t in tasks]
        assert len(set(ids)) == 50


class TestTaskManagerGet:
    async def test_returns_task_after_creation(self, tm: TaskManager):
        task = await tm.create("https://example.com")
        fetched = await tm.get(task.task_id)
        assert fetched is not None
        assert fetched.task_id == task.task_id

    async def test_returns_none_for_unknown_task_id(self, tm: TaskManager):
        result = await tm.get("nonexistent-id")
        assert result is None


class TestTaskManagerUpdate:
    async def test_updates_status_field(self, tm: TaskManager):
        task = await tm.create("https://example.com")
        await tm.update(task.task_id, status="downloading")
        updated = await tm.get(task.task_id)
        assert updated.status == "downloading"

    async def test_updates_multiple_fields_at_once(self, tm: TaskManager):
        task = await tm.create("https://example.com")
        await tm.update(task.task_id, status="completed", title="测试视频", summary="总结内容")
        updated = await tm.get(task.task_id)
        assert updated.status == "completed"
        assert updated.title == "测试视频"
        assert updated.summary == "总结内容"

    async def test_untouched_fields_remain_unchanged(self, tm: TaskManager):
        task = await tm.create("https://example.com")
        original_url = task.url
        await tm.update(task.task_id, status="transcribing")
        updated = await tm.get(task.task_id)
        assert updated.url == original_url

    async def test_updated_at_changes_after_update(self, tm: TaskManager):
        task = await tm.create("https://example.com")
        original_updated_at = task.updated_at
        await asyncio.sleep(0.01)
        await tm.update(task.task_id, status="downloading")
        updated = await tm.get(task.task_id)
        assert updated.updated_at > original_updated_at

    async def test_update_unknown_task_id_does_not_raise(self, tm: TaskManager):
        # 不应抛出异常
        await tm.update("nonexistent-id", status="failed")

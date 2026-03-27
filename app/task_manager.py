import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskRecord:
    task_id: str
    url: str
    status: str = "pending"
    title: str | None = None
    transcript_source: str | None = None
    summary: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, url: str) -> TaskRecord:
        task = TaskRecord(task_id=str(uuid.uuid4()), url=url)
        async with self._lock:
            self._tasks[task.task_id] = task
        return task

    async def get(self, task_id: str) -> TaskRecord | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update(self, task_id: str, **kwargs) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            for key, value in kwargs.items():
                setattr(task, key, value)
            task.updated_at = datetime.utcnow()


task_manager = TaskManager()

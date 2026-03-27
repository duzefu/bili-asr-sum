from datetime import datetime
from typing import Literal

from pydantic import BaseModel, HttpUrl


class SummarizeRequest(BaseModel):
    url: str


class TaskResponse(BaseModel):
    task_id: str
    status: Literal["pending", "downloading", "transcribing", "summarizing", "completed", "failed"]
    url: str
    title: str | None = None
    transcript_source: Literal["subtitle", "asr"] | None = None
    summary: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class SubmitResponse(BaseModel):
    task_id: str
    status: str

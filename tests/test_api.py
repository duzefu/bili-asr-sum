import pytest
from httpx import AsyncClient


class TestSubmitSummarize:
    async def test_returns_202_with_task_id(self, client: AsyncClient, mocker):
        mocker.patch("app.main.run_pipeline")
        resp = await client.post("/api/summarize", json={"url": "https://www.bilibili.com/video/BV1xx"})
        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    async def test_missing_url_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/summarize", json={})
        assert resp.status_code == 422

    async def test_empty_body_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/summarize", content=b"")
        assert resp.status_code == 422


class TestGetTask:
    async def test_returns_task_after_submit(self, client: AsyncClient, mocker):
        mocker.patch("app.main.run_pipeline")
        submit = await client.post("/api/summarize", json={"url": "https://example.com"})
        task_id = submit.json()["task_id"]

        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["url"] == "https://example.com"
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "updated_at" in data

    async def test_nonexistent_task_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/tasks/nonexistent-task-id")
        assert resp.status_code == 404

    async def test_response_structure_matches_schema(self, client: AsyncClient, mocker):
        mocker.patch("app.main.run_pipeline")
        submit = await client.post("/api/summarize", json={"url": "https://example.com"})
        task_id = submit.json()["task_id"]

        resp = await client.get(f"/api/tasks/{task_id}")
        data = resp.json()
        # 可选字段初始为 null
        assert data["title"] is None
        assert data["summary"] is None
        assert data["error"] is None
        assert data["transcript_source"] is None


class TestHealth:
    async def test_returns_200(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_response_contains_asr_provider(self, client: AsyncClient):
        resp = await client.get("/health")
        data = resp.json()
        assert "asr_provider" in data
        assert data["status"] == "ok"

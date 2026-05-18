"""
Integration tests for the event → webhook simulate → review flow.

Requires a running Postgres (docker compose up db -d).
Whisper and Claude are mocked — no GCS or Anthropic credentials needed.

Run:
    pytest tests/test_pipeline.py -v
"""
import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _fake_transcribe(gcs_key, content_type=None):
    return "Our new product delivers 10x performance at half the cost."


def _fake_generate_draft(transcript, event_title):
    return {
        "content": f"# {event_title}\n\nDraft based on transcript.",
        "model": "claude-opus-4-7",
        "prompt_tokens": 100,
        "completion_tokens": 60,
    }


@pytest.mark.asyncio
async def test_create_event(client):
    with patch("app.services.gcs.generate_presigned_upload_url", return_value="http://fake/upload"):
        resp = await client.post("/events", json={
            "title": "Launch Day",
            "description": "Our biggest launch yet",
            "producer_id": "producer-001",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_upload"
    assert data["presigned_upload_url"] == "http://fake/upload"
    assert data["media_gcs_key"].startswith("media/")


@pytest.mark.asyncio
async def test_full_pipeline(client):
    # 1. Create event
    with patch("app.services.gcs.generate_presigned_upload_url", return_value="http://fake/upload"):
        resp = await client.post("/events", json={
            "title": "Product Demo",
            "producer_id": "producer-001",
        })
    assert resp.status_code == 201
    event_id = resp.json()["id"]

    # 2. Simulate GCS upload notification → triggers transcription + draft
    with (
        patch("app.routers.webhooks.transcribe_gcs_object", side_effect=_fake_transcribe),
        patch("app.routers.webhooks.generate_draft", side_effect=_fake_generate_draft),
    ):
        resp = await client.post("/webhooks/gcs/simulate", json={"event_id": event_id})
        assert resp.status_code == 200
        await asyncio.sleep(1)  # allow background task to finish

    # 3. Pipeline status should be draft_ready
    resp = await client.get(f"/events/{event_id}/status")
    assert resp.status_code == 200
    s = resp.json()
    assert s["status"] == "draft_ready"
    assert s["transcript_status"] == "completed"
    assert s["draft_status"] == "completed"
    assert s["review_decision"] is None

    # 4. Fetch draft
    resp = await client.get(f"/drafts/by-event/{event_id}")
    assert resp.status_code == 200
    draft = resp.json()
    assert "Product Demo" in draft["content"]
    draft_id = draft["id"]

    # 5. Reviewer adds a comment
    resp = await client.post(f"/reviews/by-draft/{draft_id}/comments", json={
        "author_id": "reviewer-001",
        "author_role": "reviewer",
        "body": "Looks great, minor tweak on the CTA.",
    })
    assert resp.status_code == 201

    # 6. Reviewer approves
    resp = await client.post(f"/reviews/by-draft/{draft_id}/decision", json={
        "reviewer_id": "reviewer-001",
        "decision": "approved",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "approved"

    # 7. Event should now be approved
    resp = await client.get(f"/events/{event_id}/status")
    s = resp.json()
    assert s["status"] == "approved"
    assert s["review_decision"] == "approved"


@pytest.mark.asyncio
async def test_duplicate_decision_rejected(client):
    with patch("app.services.gcs.generate_presigned_upload_url", return_value="http://fake/upload"):
        resp = await client.post("/events", json={"title": "Test", "producer_id": "p1"})
    event_id = resp.json()["id"]

    with (
        patch("app.routers.webhooks.transcribe_gcs_object", side_effect=_fake_transcribe),
        patch("app.routers.webhooks.generate_draft", side_effect=_fake_generate_draft),
    ):
        await client.post("/webhooks/gcs/simulate", json={"event_id": event_id})
        await asyncio.sleep(1)

    draft_id = (await client.get(f"/drafts/by-event/{event_id}")).json()["id"]
    payload = {"reviewer_id": "r1", "decision": "approved"}
    assert (await client.post(f"/reviews/by-draft/{draft_id}/decision", json=payload)).status_code == 200
    assert (await client.post(f"/reviews/by-draft/{draft_id}/decision", json=payload)).status_code == 409

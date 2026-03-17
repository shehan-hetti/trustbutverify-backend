"""Integration tests for all API endpoints.

Uses an in-memory SQLite database (see conftest.py) so Docker is not required.
"""

import json

import pytest
from httpx import AsyncClient


# ─── Health ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


# ─── Participant registration & verification ─────────────────────────

@pytest.mark.asyncio
async def test_register_participant(client: AsyncClient):
    res = await client.post("/api/participants/register")
    assert res.status_code == 201
    data = res.json()
    assert "participant_uuid" in data
    assert len(data["participant_uuid"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_verify_participant_valid(client: AsyncClient):
    # Register first
    reg = await client.post("/api/participants/register")
    uuid = reg.json()["participant_uuid"]

    res = await client.get(f"/api/participants/verify/{uuid}")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert "registered_at" in data


@pytest.mark.asyncio
async def test_verify_participant_invalid(client: AsyncClient):
    res = await client.get("/api/participants/verify/nonexistent-uuid")
    assert res.status_code == 404


# ─── Sync ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_requires_participant_header(client: AsyncClient):
    """Sync without X-Participant-UUID header should fail (422 — missing header)."""
    res = await client.post("/api/sync", json={"conversations": [], "nudgeEvents": []})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_sync_rejects_unknown_participant(client: AsyncClient):
    res = await client.post(
        "/api/sync",
        json={"conversations": [], "nudgeEvents": []},
        headers={"X-Participant-UUID": "fake-uuid"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_sync_empty_payload(client: AsyncClient):
    """Sync with valid participant and empty payload succeeds."""
    reg = await client.post("/api/participants/register")
    uuid = reg.json()["participant_uuid"]

    res = await client.post(
        "/api/sync",
        json={"conversations": [], "nudgeEvents": []},
        headers={"X-Participant-UUID": uuid},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["counts"]["conversations"] == 0


@pytest.mark.asyncio
async def test_sync_conversation_with_turns(client: AsyncClient):
    """Sync a conversation with turns and verify counts."""
    reg = await client.post("/api/participants/register")
    uuid = reg.json()["participant_uuid"]

    payload = {
        "conversations": [
            {
                "id": "chatgpt.com::thread-1",
                "platform": "ChatGPT",
                "domain": "chatgpt.com",
                "url": "https://chatgpt.com/c/thread-1",
                "createdAt": 1704067200000,
                "lastUpdatedAt": 1704067260000,
                "turns": [
                    {
                        "id": "turn-1",
                        "prompt": {"text": "Hello", "textLength": 5, "ts": 1704067200000},
                        "response": {
                            "text": "Hi there!",
                            "textLength": 9,
                            "ts": 1704067210000,
                            "readability": {
                                "version": 1,
                                "sampleTextLength": 9,
                                "sentenceCount": 1,
                                "wordCount": 2,
                                "fleschReadingEase": 100.0,
                                "fleschKincaidGrade": 0.5,
                                "smogIndex": 0,
                                "colemanLiauIndex": -5.0,
                                "automatedReadabilityIndex": -3.0,
                                "gunningFog": 1.0,
                                "daleChallReadabilityScore": 2.0,
                                "lix": 10.0,
                                "rix": 0.0,
                                "textStandard": "Kindergarten",
                                "textMedian": 1.0,
                            },
                            "complexity": {
                                "gradeConsensus": 1.0,
                                "complexityBand": "very-easy",
                            },
                        },
                        "responseTimeMs": 10000,
                        "ts": 1704067210000,
                    }
                ],
                "copyActivities": [
                    {
                        "id": "copy-1",
                        "timestamp": 1704067220000,
                        "domain": "chatgpt.com",
                        "url": "https://chatgpt.com/c/thread-1",
                        "conversationId": "chatgpt.com::thread-1",
                        "turnId": "turn-1",
                        "turnSide": "response",
                        "textLength": 9,
                        "copyCategory": "Greeting",
                        "copyCategorySource": "llm",
                    }
                ],
            }
        ],
        "nudgeEvents": [
            {
                "id": "ne-1",
                "timestamp": 1704067230000,
                "domain": "chatgpt.com",
                "conversationId": "chatgpt.com::thread-1",
                "turnId": "turn-1",
                "triggerType": "copy",
                "nudgeQuestionId": "copy-confidence-1",
                "nudgeQuestionText": "Did you copy this because you trust this response?",
                "questionTags": ["accountability", "self-reflection"],
                "response": "yes",
                "responseTimeMs": 1500,
                "dismissedBy": "answer",
            }
        ],
    }

    res = await client.post(
        "/api/sync",
        json=payload,
        headers={"X-Participant-UUID": uuid},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["counts"]["conversations"] >= 1
    assert data["counts"]["turns"] == 1
    assert data["counts"]["copyActivities"] == 1
    assert data["counts"]["nudgeEvents"] == 1

    debug = await client.get(f"/api/debug/data?participant_uuid={uuid}")
    assert debug.status_code == 200
    nudge_events = debug.json()["nudge_events"]
    assert len(nudge_events) == 1
    tags = nudge_events[0]["question_tags"]
    if isinstance(tags, str):
        tags = json.loads(tags)
    assert tags == ["accountability", "self-reflection"]


@pytest.mark.asyncio
async def test_sync_idempotent(client: AsyncClient):
    """Syncing the same data twice should not duplicate records."""
    reg = await client.post("/api/participants/register")
    uuid = reg.json()["participant_uuid"]

    payload = {
        "conversations": [
            {
                "id": "chatgpt.com::thread-2",
                "platform": "ChatGPT",
                "domain": "chatgpt.com",
                "createdAt": 1704067200000,
                "lastUpdatedAt": 1704067260000,
                "turns": [
                    {
                        "id": "turn-x",
                        "prompt": {"ts": 1704067200000},
                        "response": {"ts": 1704067210000},
                        "ts": 1704067210000,
                    }
                ],
                "copyActivities": [
                    {
                        "id": "copy-x",
                        "timestamp": 1704067220000,
                    }
                ],
            }
        ],
        "nudgeEvents": [],
    }

    headers = {"X-Participant-UUID": uuid}

    # First sync
    res1 = await client.post("/api/sync", json=payload, headers=headers)
    assert res1.status_code == 200
    counts1 = res1.json()["counts"]

    # Second sync — same data
    res2 = await client.post("/api/sync", json=payload, headers=headers)
    assert res2.status_code == 200
    counts2 = res2.json()["counts"]

    # Turns and copies should not be duplicated
    assert counts2["turns"] == 0  # already exists
    assert counts2["copyActivities"] == 0  # already exists


@pytest.mark.asyncio
async def test_sync_updates_turn_category(client: AsyncClient):
    """Re-syncing a turn with updated category should update the record."""
    reg = await client.post("/api/participants/register")
    uuid = reg.json()["participant_uuid"]
    headers = {"X-Participant-UUID": uuid}

    base_turn = {
        "id": "turn-upd",
        "prompt": {"ts": 1704067200000},
        "response": {"ts": 1704067210000},
        "ts": 1704067210000,
    }

    # First sync — no category
    payload1 = {
        "conversations": [{
            "id": "t-upd",
            "createdAt": 1704067200000,
            "lastUpdatedAt": 1704067260000,
            "turns": [base_turn],
            "copyActivities": [],
        }],
        "nudgeEvents": [],
    }
    await client.post("/api/sync", json=payload1, headers=headers)

    # Second sync — with category
    base_turn_updated = {**base_turn, "category": "Code|Python", "summary": "User asked about Python."}
    payload2 = {
        "conversations": [{
            "id": "t-upd",
            "createdAt": 1704067200000,
            "lastUpdatedAt": 1704067300000,
            "turns": [base_turn_updated],
            "copyActivities": [],
        }],
        "nudgeEvents": [],
    }
    res = await client.post("/api/sync", json=payload2, headers=headers)
    assert res.status_code == 200


# ─── Debug endpoint ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_debug_data_endpoint(client: AsyncClient):
    """Debug endpoint returns structured data."""
    res = await client.get("/api/debug/data")
    assert res.status_code == 200
    data = res.json()
    assert "participants" in data
    assert "conversations" in data
    assert "counts" in data

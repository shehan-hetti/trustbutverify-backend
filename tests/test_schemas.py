"""Tests for Pydantic schemas — validates parsing, defaults, and validation."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    PromptData,
    ResponseData,
    TurnPayload,
    CopyActivityPayload,
    ConversationPayload,
    NudgeEventPayload,
    SyncRequest,
    SyncCounts,
    SyncResponse,
    HealthResponse,
    ParticipantRegisterResponse,
)


class TestPromptData:
    def test_minimal(self):
        p = PromptData(ts=1704067200000)
        assert p.ts == 1704067200000
        assert p.text is None
        assert p.textLength is None

    def test_full(self):
        p = PromptData(text="hello", textLength=5, ts=100)
        assert p.text == "hello"


class TestResponseData:
    def test_with_readability(self):
        r = ResponseData(
            ts=100,
            text="answer",
            readability={"version": 1, "wordCount": 50},
            complexity={"gradeConsensus": 8, "complexityBand": "moderate"},
        )
        assert r.readability["version"] == 1
        assert r.complexity["complexityBand"] == "moderate"


class TestTurnPayload:
    def test_minimal(self):
        t = TurnPayload(
            id="turn-1",
            prompt=PromptData(ts=100),
            response=ResponseData(ts=200),
            ts=200,
        )
        assert t.id == "turn-1"
        assert t.category is None
        assert t.previousTurnId is None

    def test_missing_id_raises(self):
        with pytest.raises(ValidationError):
            TurnPayload(
                prompt=PromptData(ts=100),
                response=ResponseData(ts=200),
                ts=200,
            )


class TestCopyActivityPayload:
    def test_minimal(self):
        c = CopyActivityPayload(id="copy-1", timestamp=100)
        assert c.id == "copy-1"
        assert c.domain is None
        assert c.readability is None

    def test_full(self):
        c = CopyActivityPayload(
            id="copy-2",
            timestamp=100,
            domain="chatgpt.com",
            url="https://chatgpt.com/c/abc",
            conversationId="chatgpt.com::abc",
            turnId="turn-1",
            turnSide="response",
            textLength=42,
            copyCategory="Code|Python",
            copyCategorySource="llm",
            readability={"version": 1},
            complexity={"gradeConsensus": 8},
        )
        assert c.turnSide == "response"
        assert c.copyCategorySource == "llm"


class TestConversationPayload:
    def test_with_turns_and_copies(self):
        c = ConversationPayload(
            id="thread-1",
            platform="ChatGPT",
            domain="chatgpt.com",
            createdAt=100,
            lastUpdatedAt=200,
            turns=[
                TurnPayload(
                    id="t1",
                    prompt=PromptData(ts=100),
                    response=ResponseData(ts=200),
                    ts=200,
                )
            ],
            copyActivities=[
                CopyActivityPayload(id="c1", timestamp=150)
            ],
        )
        assert len(c.turns) == 1
        assert len(c.copyActivities) == 1

    def test_defaults_to_empty_lists(self):
        c = ConversationPayload(
            id="thread-2",
            createdAt=100,
            lastUpdatedAt=200,
        )
        assert c.turns == []
        assert c.copyActivities == []


class TestNudgeEventPayload:
    def test_minimal(self):
        n = NudgeEventPayload(
            id="ne-1",
            timestamp=100,
            triggerType="copy",
            nudgeQuestionId="q1",
            nudgeQuestionText="Did you trust this?",
        )
        assert n.triggerType == "copy"
        assert n.response is None

    def test_with_numeric_response(self):
        n = NudgeEventPayload(
            id="ne-2",
            timestamp=100,
            triggerType="response",
            nudgeQuestionId="q2",
            nudgeQuestionText="How clear?",
            response=8,
            responseTimeMs=1200,
            dismissedBy="answer",
        )
        assert n.response == 8


class TestSyncRequest:
    def test_empty(self):
        s = SyncRequest()
        assert s.conversations == []
        assert s.nudgeEvents == []

    def test_with_data(self):
        s = SyncRequest(
            conversations=[
                ConversationPayload(id="t1", createdAt=100, lastUpdatedAt=200)
            ],
            nudgeEvents=[
                NudgeEventPayload(
                    id="ne-1",
                    timestamp=100,
                    triggerType="copy",
                    nudgeQuestionId="q1",
                    nudgeQuestionText="Trust?",
                )
            ],
        )
        assert len(s.conversations) == 1
        assert len(s.nudgeEvents) == 1


class TestSyncCounts:
    def test_defaults_to_zero(self):
        c = SyncCounts()
        assert c.conversations == 0
        assert c.turns == 0
        assert c.copyActivities == 0
        assert c.nudgeEvents == 0


class TestSyncResponse:
    def test_structure(self):
        r = SyncResponse(
            success=True,
            counts=SyncCounts(conversations=1, turns=2, copyActivities=3, nudgeEvents=4),
            message="Synced OK",
        )
        assert r.success is True
        assert r.counts.turns == 2


class TestHealthResponse:
    def test_structure(self):
        h = HealthResponse(status="ok", database="connected")
        assert h.status == "ok"


class TestParticipantRegisterResponse:
    def test_structure(self):
        p = ParticipantRegisterResponse(participant_uuid="abc-123")
        assert p.participant_uuid == "abc-123"
        assert p.message == "Registered successfully"

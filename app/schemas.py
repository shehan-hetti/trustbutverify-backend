"""Pydantic schemas for API request / response validation.

These map directly to the browser extension's data structures,
accepting what the plugin sends and transforming it for DB storage.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Shared / reusable
# ------------------------------------------------------------------

class PromptData(BaseModel):
    """Prompt portion of a conversation turn (from browser)."""
    text: str | None = None
    textLength: int | None = None
    ts: int  # epoch ms


class ResponseData(BaseModel):
    """Response portion of a conversation turn (from browser)."""
    text: str | None = None
    textLength: int | None = None
    ts: int  # epoch ms
    readability: dict[str, Any] | None = None
    complexity: dict[str, Any] | None = None


# ------------------------------------------------------------------
# Sync payload: incoming data from the browser extension
# ------------------------------------------------------------------

class TurnPayload(BaseModel):
    """A single conversation turn as sent by the plugin."""
    id: str
    previousTurnId: str | None = None
    prompt: PromptData
    response: ResponseData
    responseTimeMs: int | None = None
    category: str | None = None
    summary: str | None = None
    ts: int  # epoch ms


class CopyActivityPayload(BaseModel):
    """A single copy activity as sent by the plugin."""
    id: str                                     # client-generated activity ID
    timestamp: int                              # epoch ms
    domain: str | None = None
    url: str | None = None
    conversationId: str | None = None           # thread_id
    turnId: str | None = None
    turnSide: str | None = None                 # 'prompt' or 'response'
    textLength: int | None = None               # selection length
    containerTextLength: int | None = None
    isFullText: bool | None = None              # future: full vs partial copy
    copyCategory: str | None = None
    copyCategorySource: str | None = None       # 'llm' or 'turn'
    readability: dict[str, Any] | None = None
    complexity: dict[str, Any] | None = None


class ConversationPayload(BaseModel):
    """A single conversation log as sent by the plugin."""
    id: str                                     # thread_id
    platform: str | None = None
    domain: str | None = None
    url: str | None = None
    title: str | None = None
    createdAt: int                              # epoch ms
    lastUpdatedAt: int                          # epoch ms
    turns: list[TurnPayload] = Field(default_factory=list)
    copyActivities: list[CopyActivityPayload] = Field(default_factory=list)


class NudgeEventPayload(BaseModel):
    """A single nudge/ESM event as sent by the plugin."""
    id: str                                     # client-generated event ID
    timestamp: int                              # epoch ms
    domain: str | None = None
    conversationId: str | None = None           # thread_id
    turnId: str | None = None
    copyActivityId: str | None = None
    triggerType: str                            # 'copy' or 'response'
    nudgeQuestionId: str
    nudgeQuestionText: str
    questionTags: list[str] | None = None
    response: str | int | None = None           # yes/no/partly/skip or 1-10
    responseTimeMs: int | None = None
    dismissedBy: str | None = None              # answer/skip/close/timeout/replaced


class SyncRequest(BaseModel):
    """Full sync payload from the browser extension."""
    conversations: list[ConversationPayload] = Field(default_factory=list)
    nudgeEvents: list[NudgeEventPayload] = Field(default_factory=list)


# ------------------------------------------------------------------
# Responses
# ------------------------------------------------------------------

class SyncCounts(BaseModel):
    conversations: int = 0
    turns: int = 0
    copyActivities: int = 0
    nudgeEvents: int = 0


class SyncResponse(BaseModel):
    success: bool
    counts: SyncCounts
    message: str = ""


class ParticipantRegisterResponse(BaseModel):
    participant_uuid: str
    message: str = "Registered successfully"


class HealthResponse(BaseModel):
    status: str
    database: str

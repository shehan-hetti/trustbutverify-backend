"""Core sync logic — upserts browser extension data into MySQL.

All timestamps from the plugin are epoch milliseconds.
MySQL DATETIME(3) stores millisecond precision, so we convert:
  epoch_ms → datetime via datetime.utcfromtimestamp(epoch_ms / 1000)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, ConversationTurn, CopyActivity, NudgeEvent
from app.schemas import (
    ConversationPayload,
    CopyActivityPayload,
    NudgeEventPayload,
    SyncCounts,
)

logger = logging.getLogger(__name__)


def _ms_to_dt(epoch_ms: int) -> datetime:
    """Convert epoch milliseconds to a UTC datetime."""
    return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)


# ------------------------------------------------------------------
# Readability / complexity flattening helpers
# ------------------------------------------------------------------

def _flatten_readability(r: dict[str, Any] | None, prefix: str = "") -> dict[str, Any]:
    """Extract readability dict fields into flat column kwargs.

    *prefix* is prepended to each key (e.g. "resp_" for conversation turns).
    """
    if not r:
        return {}
    return {
        f"{prefix}readability_version": r.get("version"),
        f"{prefix}sample_text_length": r.get("sampleTextLength"),
        f"{prefix}sentence_count": r.get("sentenceCount"),
        f"{prefix}word_count": r.get("wordCount"),
        f"{prefix}flesch_reading_ease": r.get("fleschReadingEase"),
        f"{prefix}flesch_kincaid_grade": r.get("fleschKincaidGrade"),
        f"{prefix}smog_index": r.get("smogIndex"),
        f"{prefix}coleman_liau_index": r.get("colemanLiauIndex"),
        f"{prefix}automated_readability": r.get("automatedReadabilityIndex"),
        f"{prefix}gunning_fog": r.get("gunningFog"),
        f"{prefix}dale_chall_score": r.get("daleChallReadabilityScore"),
        f"{prefix}lix": r.get("lix"),
        f"{prefix}rix": r.get("rix"),
        f"{prefix}text_standard": r.get("textStandard"),
        f"{prefix}text_median": r.get("textMedian"),
    }


def _flatten_complexity(c: dict[str, Any] | None, prefix: str = "") -> dict[str, Any]:
    """Extract complexity dict fields into flat column kwargs."""
    if not c:
        return {}
    reason = c.get("reasonCodes")
    return {
        f"{prefix}grade_consensus": c.get("gradeConsensus"),
        f"{prefix}complexity_band": c.get("complexityBand"),
        f"{prefix}reason_codes": ",".join(reason) if isinstance(reason, list) else reason,
    }


# ------------------------------------------------------------------
# Conversations + turns
# ------------------------------------------------------------------
async def upsert_conversations(
    db: AsyncSession,
    participant_id: int,
    conversations: list[ConversationPayload],
) -> tuple[int, int, int]:
    """
    Upsert conversations and their turns + embedded copy activities.

    Returns (conversations_count, turns_count, copy_count).
    """
    conv_count = 0
    turn_count = 0
    copy_count = 0

    for conv_payload in conversations:
        # Check if conversation already exists for this participant
        result = await db.execute(
            select(Conversation).where(
                Conversation.participant_id == participant_id,
                Conversation.thread_id == conv_payload.id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update mutable fields
            existing.last_seen_at = _ms_to_dt(conv_payload.lastUpdatedAt)
            if conv_payload.platform:
                existing.platform = conv_payload.platform
            if conv_payload.url:
                existing.url = conv_payload.url
            if conv_payload.title:
                existing.title = conv_payload.title
            conversation = existing
        else:
            conversation = Conversation(
                participant_id=participant_id,
                thread_id=conv_payload.id,
                platform=conv_payload.platform,
                domain=conv_payload.domain,
                url=conv_payload.url,
                title=conv_payload.title,
                first_seen_at=_ms_to_dt(conv_payload.createdAt),
                last_seen_at=_ms_to_dt(conv_payload.lastUpdatedAt),
            )
            db.add(conversation)
            await db.flush()  # get conversation.id
            conv_count += 1

        if not existing:
            conv_count = conv_count  # already counted above
        else:
            conv_count += 1

        # Upsert turns
        for turn_payload in conv_payload.turns:
            turn_result = await db.execute(
                select(ConversationTurn).where(
                    ConversationTurn.turn_id == turn_payload.id,
                )
            )
            existing_turn = turn_result.scalar_one_or_none()

            if existing_turn:
                # Update fields that may change (category/summary can go from "pending" to real)
                if turn_payload.category:
                    existing_turn.category = turn_payload.category
                if turn_payload.summary:
                    existing_turn.summary = turn_payload.summary
                if turn_payload.response.readability:
                    for k, v in _flatten_readability(turn_payload.response.readability, "resp_").items():
                        setattr(existing_turn, k, v)
                if turn_payload.response.complexity:
                    for k, v in _flatten_complexity(turn_payload.response.complexity, "resp_").items():
                        setattr(existing_turn, k, v)
            else:
                turn = ConversationTurn(
                    conversation_id=conversation.id,
                    turn_id=turn_payload.id,
                    previous_turn_id=turn_payload.previousTurnId,
                    prompt_ts=_ms_to_dt(turn_payload.prompt.ts),
                    response_ts=_ms_to_dt(turn_payload.response.ts),
                    response_time_ms=turn_payload.responseTimeMs,
                    prompt_text_len=turn_payload.prompt.textLength,
                    response_text_len=turn_payload.response.textLength,
                    category=turn_payload.category,
                    summary=turn_payload.summary,
                    **_flatten_readability(turn_payload.response.readability, "resp_"),
                    **_flatten_complexity(turn_payload.response.complexity, "resp_"),
                )
                db.add(turn)
                turn_count += 1

        # Upsert embedded copy activities
        for copy_payload in conv_payload.copyActivities:
            c = await _upsert_copy_activity(db, participant_id, copy_payload)
            copy_count += c

    return conv_count, turn_count, copy_count


# ------------------------------------------------------------------
# Copy activities
# ------------------------------------------------------------------
async def _upsert_copy_activity(
    db: AsyncSession,
    participant_id: int,
    payload: CopyActivityPayload,
) -> int:
    """Upsert a single copy activity. Returns 1 if inserted, 0 if already exists."""
    result = await db.execute(
        select(CopyActivity).where(
            CopyActivity.participant_id == participant_id,
            CopyActivity.activity_id == payload.id,
        )
    )
    if result.scalar_one_or_none():
        return 0  # already exists, skip

    activity = CopyActivity(
        participant_id=participant_id,
        activity_id=payload.id,
        occurred_at=_ms_to_dt(payload.timestamp),
        domain=payload.domain,
        url=payload.url,
        thread_id=payload.conversationId,
        turn_id=payload.turnId,
        turn_side=payload.turnSide,
        selection_len=payload.textLength,
        container_text_len=payload.containerTextLength,
        is_full_text=1 if payload.isFullText else 0,
        copy_category=payload.copyCategory,
        copy_category_source=payload.copyCategorySource,
        **_flatten_readability(payload.readability),
        **_flatten_complexity(payload.complexity),
    )
    db.add(activity)
    return 1


# ------------------------------------------------------------------
# Nudge events
# ------------------------------------------------------------------
async def upsert_nudge_events(
    db: AsyncSession,
    participant_id: int,
    events: list[NudgeEventPayload],
) -> int:
    """Upsert nudge events. Returns count of newly inserted events."""
    count = 0

    for payload in events:
        result = await db.execute(
            select(NudgeEvent).where(
                NudgeEvent.participant_id == participant_id,
                NudgeEvent.event_id == payload.id,
            )
        )
        if result.scalar_one_or_none():
            continue  # already exists, skip

        event = NudgeEvent(
            participant_id=participant_id,
            event_id=payload.id,
            occurred_at=_ms_to_dt(payload.timestamp),
            domain=payload.domain,
            thread_id=payload.conversationId,
            turn_id=payload.turnId,
            copy_activity_id=payload.copyActivityId,
            trigger_type=payload.triggerType,
            question_id=payload.nudgeQuestionId,
            question_text=payload.nudgeQuestionText,
            question_tags=list(dict.fromkeys(payload.questionTags)) if payload.questionTags else None,
            response=str(payload.response) if payload.response is not None else None,
            response_time_ms=payload.responseTimeMs,
            dismissed_by=payload.dismissedBy,
        )
        db.add(event)
        count += 1

    return count


# ------------------------------------------------------------------
# Top-level sync orchestrator
# ------------------------------------------------------------------
async def process_sync(
    db: AsyncSession,
    participant_id: int,
    conversations: list[ConversationPayload],
    nudge_events: list[NudgeEventPayload],
) -> SyncCounts:
    """
    Process a full sync payload from the browser extension.
    Returns counts of upserted records.
    """
    conv_count, turn_count, copy_count = await upsert_conversations(
        db, participant_id, conversations
    )
    nudge_count = await upsert_nudge_events(db, participant_id, nudge_events)

    logger.info(
        "Sync complete: conversations=%d turns=%d copies=%d nudges=%d",
        conv_count, turn_count, copy_count, nudge_count,
    )

    return SyncCounts(
        conversations=conv_count,
        turns=turn_count,
        copyActivities=copy_count,
        nudgeEvents=nudge_count,
    )

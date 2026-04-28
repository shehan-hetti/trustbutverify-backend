from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check API and database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return HealthResponse(status="ok", database="connected")
    except Exception as exc:
        return HealthResponse(status="degraded", database=f"error: {exc}")


@router.get("/debug/data")
async def debug_data(
    participant_uuid: str = Query(None, description="Filter by participant UUID"),
    x_debug_key: str = Header(None, alias="X-Debug-Key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint — view all stored data.
    Requires X-Debug-Key header matching the DEBUG_API_KEY env var.
    Use ?participant_uuid=<uuid> to filter by participant.
    """
    if not settings.DEBUG_API_KEY or x_debug_key != settings.DEBUG_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Build participant filter using parameterized queries
    p_ids: list[int] = []
    if participant_uuid:
        participants = (await db.execute(
            text("SELECT id, participant_uuid, registered_at FROM participants WHERE participant_uuid = :uuid"),
            {"uuid": participant_uuid},
        )).mappings().all()
        p_ids = [p["id"] for p in participants]
    else:
        participants = (await db.execute(
            text("SELECT id, participant_uuid, registered_at FROM participants")
        )).mappings().all()
        p_ids = [p["id"] for p in participants]

    # Helper to build a safe IN clause
    def _in_filter(column: str, ids: list[int]) -> tuple[str, dict]:
        if not ids:
            return f"{column} IN (NULL)", {}
        placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
        params = {f"id_{i}": v for i, v in enumerate(ids)}
        return f"{column} IN ({placeholders})", params

    if participant_uuid:
        conv_clause, conv_params = _in_filter("participant_id", p_ids)
        turn_clause, turn_params = _in_filter("c.participant_id", p_ids)
    else:
        conv_clause, conv_params = "1=1", {}
        turn_clause, turn_params = "1=1", {}

    conversations = (await db.execute(
        text(
            f"SELECT id, participant_id, thread_id, platform, domain, title, first_seen_at, last_seen_at "
            f"FROM conversations WHERE {conv_clause}"
        ),
        conv_params,
    )).mappings().all()

    turns = (await db.execute(
        text(
            f"SELECT ct.id, ct.conversation_id, ct.turn_id, ct.previous_turn_id, ct.category, ct.is_inferred, "
            f"ct.prompt_text_len, ct.response_text_len, ct.response_time_ms, "
            f"ct.resp_flesch_reading_ease, ct.resp_flesch_kincaid_grade, ct.resp_smog_index, "
            f"ct.resp_gunning_fog, ct.resp_word_count, ct.resp_sentence_count, "
            f"ct.resp_grade_consensus, ct.resp_complexity_band, ct.resp_reason_codes, "
            f"ct.prompt_ts, ct.response_ts "
            f"FROM conversation_turns ct "
            f"JOIN conversations c ON ct.conversation_id = c.id "
            f"WHERE {turn_clause}"
        ),
        turn_params,
    )).mappings().all()

    copies = (await db.execute(
        text(
            f"SELECT id, participant_id, activity_id, occurred_at, domain, thread_id, turn_id, "
            f"turn_side, selection_len, container_text_len, is_full_text, copy_method, copy_category, "
            f"copy_category_source, flesch_reading_ease, flesch_kincaid_grade, smog_index, "
            f"gunning_fog, word_count, sentence_count, "
            f"grade_consensus, complexity_band, reason_codes "
            f"FROM copy_activities WHERE {conv_clause}"
        ),
        conv_params,
    )).mappings().all()

    nudges = (await db.execute(
        text(
            f"SELECT id, participant_id, event_id, occurred_at, domain, thread_id, turn_id, "
            f"copy_activity_id, trigger_type, question_id, question_text, question_tags, response, "
            f"response_time_ms, dismissed_by "
            f"FROM nudge_events WHERE {conv_clause}"
        ),
        conv_params,
    )).mappings().all()

    return {
        "participants": [dict(r) for r in participants],
        "conversations": [dict(r) for r in conversations],
        "conversation_turns": [dict(r) for r in turns],
        "copy_activities": [dict(r) for r in copies],
        "nudge_events": [dict(r) for r in nudges],
        "counts": {
            "participants": len(participants),
            "conversations": len(conversations),
            "turns": len(turns),
            "copies": len(copies),
            "nudges": len(nudges),
        },
    }

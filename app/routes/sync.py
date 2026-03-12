import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Participant
from app.schemas import SyncRequest, SyncResponse
from app.services.sync_service import process_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sync"])


async def _resolve_participant(
    db: AsyncSession,
    participant_uuid: str,
) -> int:
    """Resolve a participant UUID to its database ID. Raises 401 if not found."""
    result = await db.execute(
        select(Participant).where(Participant.participant_uuid == participant_uuid)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=401,
            detail="Invalid participant UUID. Please register first.",
        )
    return participant.id


@router.post("/sync", response_model=SyncResponse)
async def sync_data(
    payload: SyncRequest,
    x_participant_uuid: str = Header(..., alias="X-Participant-UUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a data batch from the browser extension and store it.

    The plugin sends:
    - Header: X-Participant-UUID
    - Body: { conversations: [...], nudgeEvents: [...] }

    Copy activities are embedded inside each conversation's copyActivities array.
    """
    participant_id = await _resolve_participant(db, x_participant_uuid)

    logger.info(
        "Sync request from participant %s: %d conversations, %d nudge events",
        x_participant_uuid,
        len(payload.conversations),
        len(payload.nudgeEvents),
    )

    counts = await process_sync(
        db=db,
        participant_id=participant_id,
        conversations=payload.conversations,
        nudge_events=payload.nudgeEvents,
    )

    return SyncResponse(
        success=True,
        counts=counts,
        message=f"Synced: {counts.conversations} conversations, "
                f"{counts.turns} turns, {counts.copyActivities} copies, "
                f"{counts.nudgeEvents} nudge events",
    )

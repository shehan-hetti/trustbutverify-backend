import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Participant
from app.schemas import ParticipantRegisterResponse

router = APIRouter(prefix="/api/participants", tags=["participants"])


@router.post("/register", response_model=ParticipantRegisterResponse, status_code=201)
async def register_participant(db: AsyncSession = Depends(get_db)):
    """
    Register a new participant and return a UUID.

    The plugin calls this once during initial setup.
    The returned UUID is stored in chrome.storage.local and sent
    with every subsequent sync request via X-Participant-UUID header.
    """
    participant_uuid = str(uuid.uuid4())

    participant = Participant(participant_uuid=participant_uuid)
    db.add(participant)
    await db.flush()  # assigns the auto-increment id

    return ParticipantRegisterResponse(participant_uuid=participant_uuid)


@router.get("/verify/{participant_uuid}")
async def verify_participant(
    participant_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if a participant UUID is valid and registered."""
    result = await db.execute(
        select(Participant).where(Participant.participant_uuid == participant_uuid)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return {"valid": True, "registered_at": participant.registered_at.isoformat()}

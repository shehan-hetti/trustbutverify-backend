"""SQLAlchemy ORM models — mirrors schema.sql exactly."""

from datetime import datetime

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------
# 1. Participants
# ------------------------------------------------------------------
class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    participant_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        MySQLDateTime(fsp=3), nullable=False, default=datetime.utcnow
    )

    # Relationships
    conversations = relationship("Conversation", back_populates="participant")
    copy_activities = relationship("CopyActivity", back_populates="participant")
    nudge_events = relationship("NudgeEvent", back_populates="participant")


# ------------------------------------------------------------------
# 2. Conversations
# ------------------------------------------------------------------
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participants.id"), nullable=False
    )
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(MySQLDateTime(fsp=3), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(MySQLDateTime(fsp=3), nullable=False)

    # Relationships
    participant = relationship("Participant", back_populates="conversations")
    turns = relationship("ConversationTurn", back_populates="conversation", cascade="all, delete-orphan")


# ------------------------------------------------------------------
# 3. Conversation turns
# ------------------------------------------------------------------
class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    previous_turn_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    prompt_ts: Mapped[datetime] = mapped_column(MySQLDateTime(fsp=3), nullable=False)
    response_ts: Mapped[datetime] = mapped_column(MySQLDateTime(fsp=3), nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prompt_text_len: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_text_len: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category: Mapped[str | None] = mapped_column(String(512), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Readability metrics
    resp_readability_version: Mapped[int | None] = mapped_column(TINYINT(unsigned=True), nullable=True, default=1)
    resp_sample_text_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resp_sentence_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resp_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resp_flesch_reading_ease: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_flesch_kincaid_grade: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_smog_index: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_coleman_liau_index: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_automated_readability: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_gunning_fog: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_dale_chall_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_lix: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_rix: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_text_standard: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resp_text_median: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Complexity metrics
    resp_grade_consensus: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    resp_complexity_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resp_reason_codes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        MySQLDateTime(fsp=3), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        MySQLDateTime(fsp=3), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="turns")


# ------------------------------------------------------------------
# 4. Copy activities
# ------------------------------------------------------------------
class CopyActivity(Base):
    __tablename__ = "copy_activities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participants.id"), nullable=False
    )
    activity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(MySQLDateTime(fsp=3), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    turn_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    turn_side: Mapped[str | None] = mapped_column(String(10), nullable=True)

    selection_len: Mapped[int | None] = mapped_column(Integer, nullable=True)
    container_text_len: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_full_text: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=0)

    copy_category: Mapped[str | None] = mapped_column(String(512), nullable=True)
    copy_category_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Readability metrics
    readability_version: Mapped[int | None] = mapped_column(TINYINT(unsigned=True), nullable=True, default=1)
    sample_text_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flesch_reading_ease: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    flesch_kincaid_grade: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    smog_index: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    coleman_liau_index: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    automated_readability: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    gunning_fog: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    dale_chall_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    lix: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    rix: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    text_standard: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text_median: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Complexity metrics
    grade_consensus: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    complexity_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason_codes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        MySQLDateTime(fsp=3), nullable=False, default=datetime.utcnow
    )

    # Relationships
    participant = relationship("Participant", back_populates="copy_activities")


# ------------------------------------------------------------------
# 5. Nudge events
# ------------------------------------------------------------------
class NudgeEvent(Base):
    __tablename__ = "nudge_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participants.id"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(MySQLDateTime(fsp=3), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    turn_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    copy_activity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    question_id: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    response: Mapped[str | None] = mapped_column(String(50), nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dismissed_by: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        MySQLDateTime(fsp=3), nullable=False, default=datetime.utcnow
    )

    # Relationships
    participant = relationship("Participant", back_populates="nudge_events")

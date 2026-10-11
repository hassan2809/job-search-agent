from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Outreach(Base):
    __tablename__ = "outreaches"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(20))  # disclosed_need | prospected
    # Connection must be accepted before a real message is drafted -- you can't message
    # most LinkedIn users you're not connected to. After that, every message (the first
    # pitch and every follow-up) is one continuous sequence handled by the same
    # /next-message action, cycling message_drafted -> awaiting_reply until a reply
    # comes in or the sequence is closed out.
    # connection_drafted -> connection_sent -> connection_accepted
    #   -> (message_drafted -> awaiting_reply) x up to MAX_MESSAGE_STAGES
    #   -> replied -> closed_won | closed_declined | closed_no_response
    # terminal side branches if the connection itself doesn't work out:
    #   connection_declined | connection_no_response
    status: Mapped[str] = mapped_column(String(30), default="connection_drafted")
    # How many stage-messages (see MESSAGE_STAGES in app/api/v1/outreach.py) have been sent
    # so far after connecting -- covers the first message and every follow-up alike, since
    # they're one sequence, not two different mechanisms. Manually-triggered only, never on
    # a timer; capped so it can't turn into repeated nagging.
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    outreach_id: Mapped[int] = mapped_column(ForeignKey("outreaches.id"))
    sender: Mapped[str] = mapped_column(String(10))  # me | them
    body: Mapped[str] = mapped_column(Text)
    # linkedin | email. Which channel this specific message went out on -- a lead can get both, so
    # this lives on the message, not the outreach. Defaults to "linkedin" since every message before
    # this column existed was one.
    channel: Mapped[str] = mapped_column(String(10), default="linkedin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

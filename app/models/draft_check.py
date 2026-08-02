from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DraftCheck(Base):
    """One row per draft generated, recording what the deterministic checks found.

    Deliberately a separate table rather than a column on outreach_messages. A column would only
    hold the FINAL state, so every failure the retry successfully fixed would vanish -- and those
    are the most informative ones, because they are what tells you which prompt rules keep leaking.
    A table keeps both attempts. It also needs no migration: create_all adds missing tables but
    never missing columns, and this project has no migration tool.
    """

    __tablename__ = "draft_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    outreach_id: Mapped[int] = mapped_column(ForeignKey("outreaches.id"), index=True)
    # Set once the draft is actually stored. Null means the draft was generated but not persisted.
    message_id: Mapped[int | None] = mapped_column(ForeignKey("outreach_messages.id"), nullable=True)

    kind: Mapped[str] = mapped_column(String(30))  # connection_note | staged_message | reply_suggestion
    # Which MESSAGE_STAGES step this was, for staged messages only.
    stage_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Lists of {"code": ..., "detail": ...}. `first` is what the initial draft broke, `final` what
    # survived into the stored draft -- so `first` non-empty with `final` empty means the retry
    # worked, and that difference is the whole point of keeping both.
    first_failures: Mapped[list] = mapped_column(JSON, default=list)
    final_failures: Mapped[list] = mapped_column(JSON, default=list)
    retried: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

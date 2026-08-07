from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Reflection(Base):
    """What past outreach taught, distilled once and reused until regenerated.

    Stored rather than derived because it costs an LLM call over every closed episode, and because
    it is injected into every draft: recomputing it per message would be slow and would make the
    guidance drift between two messages written minutes apart.

    `episode_count` is kept so the guidance can be shown with the evidence behind it. Advice learned
    from 30 episodes and advice learned from 300 deserve different levels of trust, and without the
    count a reader cannot tell them apart.
    """

    __tablename__ = "reflections"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_count: Mapped[int] = mapped_column(Integer)
    guidance: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_lead_source_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    origin_type: Mapped[str] = mapped_column(String(20), default="disclosed_need")  # disclosed_need | prospected
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

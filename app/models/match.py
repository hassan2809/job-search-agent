from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    fit_verdict: Mapped[str] = mapped_column(String(20))  # good_fit | maybe | not_a_fit
    # What KIND of lead this is, which decides what to ask them for -- a company that ships software
    # can hire directly, a consultant can only refer, a recruiter is briefed on other people's roles.
    # Structured rather than left in the prose of fit_reasoning because both message prompts branch
    # on it, and because it is the dimension most likely to predict which outreach actually works.
    # builds_software | sells_services | recruiter | creator | other
    lead_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fit_reasoning: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

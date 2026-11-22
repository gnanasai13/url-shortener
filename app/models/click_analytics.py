from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
if TYPE_CHECKING:
    from app.models.short_url import ShortURL

class ClickAnalytics(Base):
    __tablename__ = "click_analytics"
    __table_args__ = (
        Index("ix_click_analytics_url_timestamp", "url_id", "timestamp"),
        Index("ix_click_analytics_url_country", "url_id", "country"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("short_urls.id", ondelete="CASCADE"), index=True, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device: Mapped[str | None] = mapped_column(String(120), nullable=True)
    os: Mapped[str | None] = mapped_column(String(120), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    url: Mapped[ShortURL] = relationship(back_populates="analytics")

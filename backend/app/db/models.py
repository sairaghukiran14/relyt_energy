from datetime import datetime

from sqlalchemy import DateTime, Float, Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ActualGeneration(Base):
    """Metered national wind output per 30-minute settlement period (FUELHH)."""

    __tablename__ = "actual_generation"

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    generation_mw: Mapped[float] = mapped_column(Float)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WindForecast(Base):
    """Forecast wind output for start_time, made at publish_time (WINDFOR)."""

    __tablename__ = "wind_forecast"

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    publish_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    generation_mw: Mapped[float] = mapped_column(Float)
    horizon_h: Mapped[float] = mapped_column(Float)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_wind_forecast_publish_time", "publish_time"),)

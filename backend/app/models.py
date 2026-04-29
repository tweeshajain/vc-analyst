from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Startup(Base):
    __tablename__ = "startups"
    __table_args__ = (
        Index("ix_startups_radar_score", "radar_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(128), default="")
    stage: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(2048), default="")
    source: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    radar_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scores: Mapped[list["Score"]] = relationship(
        "Score", back_populates="startup", cascade="all, delete-orphan"
    )
    memos: Mapped[list["InvestmentMemo"]] = relationship(
        "InvestmentMemo", back_populates="startup", cascade="all, delete-orphan"
    )
    deals: Mapped[list["Deal"]] = relationship(
        "Deal", back_populates="startup", cascade="all, delete-orphan"
    )


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    startup: Mapped["Startup"] = relationship("Startup", back_populates="scores")


class InvestmentMemo(Base):
    __tablename__ = "investment_memos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    startup_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("startups.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(64), default="draft")
    company_overview: Mapped[str] = mapped_column(Text, default="")
    market_opportunity: Mapped[str] = mapped_column(Text, default="")
    business_model: Mapped[str] = mapped_column(Text, default="")
    competitive_landscape: Mapped[str] = mapped_column(Text, default="")
    differentiation_analysis: Mapped[str] = mapped_column(Text, default="")
    competitive_strengths: Mapped[str] = mapped_column(Text, default="")
    competition: Mapped[str] = mapped_column(Text, default="")
    risks: Mapped[str] = mapped_column(Text, default="")
    investment_thesis: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    startup: Mapped[Optional["Startup"]] = relationship(
        "Startup", back_populates="memos"
    )


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    round_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(64), default="sourcing")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    startup: Mapped["Startup"] = relationship("Startup", back_populates="deals")


class PipelineRun(Base):
    """Audit log for `run_daily_pipeline()` executions."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    trigger: Mapped[str] = mapped_column(String(32), default="api")
    stats_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TopStartupsSnapshot(Base):
    """Historical snapshots of radar top-startups leaderboard (append-only)."""

    __tablename__ = "top_startups_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    pipeline_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pipeline_runs.id"), nullable=True
    )
    entries_json: Mapped[str] = mapped_column(Text, default="[]")

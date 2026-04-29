from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScoreBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=128)
    value: float = Field(..., ge=0, le=100)
    notes: str = ""


class ScoreCreate(ScoreBase):
    startup_id: int


class ScoreRead(ScoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    startup_id: int
    created_at: datetime


class StartupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sector: str = ""
    stage: str = ""
    description: str = ""
    url: str = ""
    source: str = "manual"
    external_id: Optional[str] = None
    upvotes: int = 0
    comments_count: int = 0


class StartupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sector: str = ""
    stage: str = ""
    description: str = ""
    url: str = ""
    source: str = "manual"
    external_id: Optional[str] = None
    upvotes: int = 0
    comments_count: int = 0
    radar_score: float = 0.0
    created_at: datetime
    scores: list[ScoreRead] = []


class TopStartupRead(BaseModel):
    """
    Top leaderboard row: `score` is min–max normalized within the top slice;
    `radar_score` is the persisted engagement-only baseline from storage.
    """

    id: int
    name: str
    description: str
    url: str
    source: str
    upvotes: int
    comments_count: int
    radar_score: float
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized rank score (0–100)")
    ranking_reason: str = Field(..., max_length=320)
    created_at: datetime
    sector: str = ""
    stage: str = ""
    insight: str = Field(
        ...,
        max_length=200,
        description="One-line narrative summary for card UI",
    )
    why_it_matters: str = Field(
        ...,
        max_length=400,
        description="Portfolio-level priority framing",
    )
    vc_digest: str = Field(
        ...,
        max_length=900,
        description="Formatted diligence lines: name, sector, stage, qualifies, 1–10 score",
    )


class MemoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    summary: str = ""
    status: str = "draft"
    startup_id: Optional[int] = None


class MemoCreate(MemoBase):
    pass


class MemoGenerateRequest(BaseModel):
    """Body for `POST /api/memo/generate`."""

    startup_id: int = Field(..., gt=0)


class MemoRead(MemoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_overview: str = ""
    market_opportunity: str = ""
    business_model: str = ""
    competitive_landscape: str = ""
    differentiation_analysis: str = ""
    competitive_strengths: str = ""
    competition: str = ""
    risks: str = ""
    investment_thesis: str = ""
    created_at: datetime


class DealBase(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    startup_id: int
    round_name: str = ""
    status: str = "sourcing"
    notes: str = ""


class DealCreate(DealBase):
    pass


class DealRead(DealBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class TopDealRead(BaseModel):
    """Deal Finder: ranked startup opportunity view."""

    startup_id: int
    name: str
    score: float = Field(..., ge=0.0, le=100.0, description="Composite deal score")
    stage: Literal["early", "growth"]
    rationale: str = Field(..., max_length=320)
    why_it_matters: str = Field(
        ...,
        max_length=400,
        description="Portfolio-level takeaway for prioritization",
    )


class TrendThemeRead(BaseModel):
    """Single recurring theme across startup narratives."""

    label: str
    description: str
    count: int = Field(..., ge=0)
    share: float = Field(..., ge=0.0, le=1.0)
    examples: list[str] = Field(default_factory=list)


class TrendsRead(BaseModel):
    """Cross-startup theme aggregation for the Top Trends panel."""

    startup_pool_size: int
    headline: str
    themes: list[TrendThemeRead]

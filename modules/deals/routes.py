from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Deal, Startup
from backend.app.schemas import DealCreate, DealRead, TopDealRead
from modules.deals.deal_scoring import (
    filter_startups_for_top_deals,
    parse_industry_query,
    parse_stage_query,
    rank_investment_worthy,
)

router = APIRouter()

_TOP_STARTUP_POOL = 600


@router.get("/top", response_model=list[TopDealRead])
def deals_top(
    industry: str | None = Query(
        None,
        description="Filter by industry: AI, SaaS, or health (case-insensitive).",
    ),
    stage: str | None = Query(
        None,
        description="Filter by fundraising label on the startup: pre-seed or seed.",
    ),
    db: Session = Depends(get_db),
):
    """
    Top 5 investment-worthy startups (after optional filters) by composite deal score.
    Example: `GET /deals/top?industry=AI&stage=seed`
    """
    try:
        ind = parse_industry_query(industry)
        stg = parse_stage_query(stage)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    startups = db.query(Startup).limit(_TOP_STARTUP_POOL).all()
    startups = filter_startups_for_top_deals(startups, ind, stg)
    ranked = rank_investment_worthy(startups, limit=5)
    return [
        TopDealRead(
            startup_id=r.startup_id,
            name=r.name,
            score=r.deal_score,
            stage=r.stage,
            rationale=r.rationale,
            why_it_matters=r.why_it_matters,
        )
        for r in ranked
    ]


@router.get("/deals", response_model=list[DealRead])
def list_deals(db: Session = Depends(get_db)):
    return db.query(Deal).order_by(Deal.created_at.desc()).all()


@router.post("/deals", response_model=DealRead, status_code=status.HTTP_201_CREATED)
def create_deal(body: DealCreate, db: Session = Depends(get_db)):
    if not db.query(Startup).filter(Startup.id == body.startup_id).first():
        raise HTTPException(status_code=404, detail="Startup not found")
    d = Deal(
        startup_id=body.startup_id,
        label=body.label,
        round_name=body.round_name,
        status=body.status,
        notes=body.notes,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.get("/deals/{deal_id}", response_model=DealRead)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    d = db.query(Deal).filter(Deal.id == deal_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deal not found")
    return d

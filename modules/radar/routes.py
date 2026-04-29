from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.app.database import get_db
from backend.app.models import Score, Startup
from backend.app.schemas import (
    ScoreCreate,
    ScoreRead,
    StartupCreate,
    StartupRead,
    TopStartupRead,
    TrendsRead,
    TrendThemeRead,
)
from modules.radar.company_filter import startup_is_company_candidate
from modules.radar.ranking import build_top_startups_read
from modules.radar.scoring import compute_radar_score
from modules.radar.trends import build_trends

router = APIRouter()

_TOP_STARTUPS_POOL = 800
_TRENDS_POOL = 500


@router.get("/startups", response_model=list[StartupRead])
def list_startups(db: Session = Depends(get_db)):
    rows = (
        db.query(Startup)
        .options(joinedload(Startup.scores))
        .order_by(Startup.created_at.desc())
        .all()
    )
    return [s for s in rows if startup_is_company_candidate(s.source or "", s.name or "", s.url)]


@router.get("/top-startups", response_model=list[TopStartupRead])
def top_startups(db: Session = Depends(get_db)):
    """
    Top 10 after deduplication, keyword-boosted composite ranking,
    and min–max normalization across that leaderboard slice.
    """
    rows = db.query(Startup).limit(_TOP_STARTUPS_POOL).all()
    rows = [s for s in rows if startup_is_company_candidate(s.source or "", s.name or "", s.url)]
    return build_top_startups_read(rows, limit=10, candidate_cap=_TOP_STARTUPS_POOL)


@router.get("/trends", response_model=TrendsRead)
def trends(db: Session = Depends(get_db)):
    """Cross-startup keyword themes for market pulse (demo narrative layer)."""
    rows = db.query(Startup).limit(_TRENDS_POOL).all()
    rows = [s for s in rows if startup_is_company_candidate(s.source or "", s.name or "", s.url)]
    theme_rows, headline, n = build_trends(rows)
    return TrendsRead(
        startup_pool_size=n,
        headline=headline,
        themes=[TrendThemeRead(**t) for t in theme_rows],
    )


@router.post("/startups", response_model=StartupRead, status_code=status.HTTP_201_CREATED)
def create_startup(body: StartupCreate, db: Session = Depends(get_db)):
    rs = compute_radar_score(body.upvotes, body.comments_count)
    s = Startup(
        name=body.name,
        sector=body.sector,
        stage=body.stage,
        description=body.description,
        url=body.url,
        source=body.source,
        external_id=body.external_id,
        upvotes=body.upvotes,
        comments_count=body.comments_count,
        radar_score=rs,
    )
    db.add(s)
    db.commit()
    return (
        db.query(Startup)
        .options(joinedload(Startup.scores))
        .filter(Startup.id == s.id)
        .first()
    )


@router.get("/startups/{startup_id}", response_model=StartupRead)
def get_startup(startup_id: int, db: Session = Depends(get_db)):
    s = (
        db.query(Startup)
        .options(joinedload(Startup.scores))
        .filter(Startup.id == startup_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Startup not found")
    return s


@router.post("/scores", response_model=ScoreRead, status_code=status.HTTP_201_CREATED)
def create_score(body: ScoreCreate, db: Session = Depends(get_db)):
    startup = db.query(Startup).filter(Startup.id == body.startup_id).first()
    if not startup:
        raise HTTPException(status_code=404, detail="Startup not found")
    sc = Score(
        startup_id=body.startup_id,
        category=body.category,
        value=body.value,
        notes=body.notes,
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


@router.get("/startups/{startup_id}/scores", response_model=list[ScoreRead])
def list_scores_for_startup(startup_id: int, db: Session = Depends(get_db)):
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise HTTPException(status_code=404, detail="Startup not found")
    return (
        db.query(Score)
        .filter(Score.startup_id == startup_id)
        .order_by(Score.created_at.desc())
        .all()
    )

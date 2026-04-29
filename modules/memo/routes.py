import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import InvestmentMemo, Startup
from backend.app.schemas import MemoCreate, MemoGenerateRequest, MemoRead
from modules.memo.generator import generate_memo
from modules.memo.pdf_export import memo_to_pdf_bytes

router = APIRouter()


@router.post("/generate", response_model=MemoRead, status_code=status.HTTP_201_CREATED)
def memo_generate(body: MemoGenerateRequest, db: Session = Depends(get_db)):
    """Generate a structured VC-style memo from startup data and persist it."""
    startup = db.query(Startup).filter(Startup.id == body.startup_id).first()
    if not startup:
        raise HTTPException(status_code=404, detail="Startup not found")
    content = generate_memo(startup, db)
    memo = InvestmentMemo(
        startup_id=startup.id,
        title=content.title,
        summary=content.executive_summary,
        status="generated",
        company_overview=content.company_overview,
        market_opportunity=content.market_opportunity,
        business_model=content.business_model,
        competitive_landscape=content.competitive_landscape,
        differentiation_analysis=content.differentiation_analysis,
        competitive_strengths=content.competitive_strengths,
        competition=content.competition,
        risks=content.risks,
        investment_thesis=content.investment_thesis,
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return memo


@router.get("/memos", response_model=list[MemoRead])
def list_memos(db: Session = Depends(get_db)):
    return (
        db.query(InvestmentMemo).order_by(InvestmentMemo.created_at.desc()).all()
    )


@router.post("/memos", response_model=MemoRead, status_code=status.HTTP_201_CREATED)
def create_memo(body: MemoCreate, db: Session = Depends(get_db)):
    if body.startup_id is not None:
        if not db.query(Startup).filter(Startup.id == body.startup_id).first():
            raise HTTPException(status_code=404, detail="Startup not found")
    m = InvestmentMemo(
        title=body.title,
        summary=body.summary,
        status=body.status,
        startup_id=body.startup_id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/memos/{memo_id}", response_model=MemoRead)
def get_memo(memo_id: int, db: Session = Depends(get_db)):
    m = db.query(InvestmentMemo).filter(InvestmentMemo.id == memo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Memo not found")
    return m


@router.get("/{startup_id}/pdf")
def export_memo_pdf(startup_id: int, db: Session = Depends(get_db)):
    """Download latest memo for startup as a compact PDF attachment."""
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise HTTPException(status_code=404, detail="Startup not found")
    m = (
        db.query(InvestmentMemo)
        .filter(InvestmentMemo.startup_id == startup_id)
        .order_by(InvestmentMemo.created_at.desc())
        .first()
    )
    if not m:
        raise HTTPException(
            status_code=404,
            detail="No memo for this startup; generate one first.",
        )
    raw = memo_to_pdf_bytes(m, startup)
    fn = re.sub(r"[^\w\-.]+", "_", (startup.name or "memo").strip())[:48] + ".pdf"
    return Response(
        content=raw,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{fn}"',
            "Content-Length": str(len(raw)),
        },
    )


@router.get("/{startup_id}", response_model=MemoRead)
def get_latest_memo_for_startup(startup_id: int, db: Session = Depends(get_db)):
    """
    Latest investment memo for this startup (by `created_at`).
    Maps to `GET /api/memo/{startup_id}` when the router prefix is `/api/memo`.
    """
    if not db.query(Startup).filter(Startup.id == startup_id).first():
        raise HTTPException(status_code=404, detail="Startup not found")
    m = (
        db.query(InvestmentMemo)
        .filter(InvestmentMemo.startup_id == startup_id)
        .order_by(InvestmentMemo.created_at.desc())
        .first()
    )
    if not m:
        raise HTTPException(
            status_code=404,
            detail="No memo found for this startup; POST /api/memo/generate first.",
        )
    return m

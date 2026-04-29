"""Render investment memo as PDF (UTF-8 safe via fpdf2)."""

from __future__ import annotations

import re
from fpdf import FPDF

from backend.app.models import InvestmentMemo, Startup

_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Executive summary", "summary"),
    ("Company overview", "company_overview"),
    ("Market opportunity", "market_opportunity"),
    ("Business model", "business_model"),
    ("Competitive landscape", "competitive_landscape"),
    ("Differentiation analysis", "differentiation_analysis"),
    ("Strengths vs competitors", "competitive_strengths"),
    ("Market structure & competition", "competition"),
    ("Risks", "risks"),
    ("Investment thesis", "investment_thesis"),
)


def _txt(val: str | None) -> str:
    s = (val or "").strip()
    if not s:
        return ""
    # FPDF core fonts: avoid unsupported glyphs for demo stability
    return re.sub(r"[^\x09\x0a\x0d\x20-\x7e\u00a0-\u00ff]", "?", s)


def memo_to_pdf_bytes(memo: InvestmentMemo, startup: Startup | None) -> bytes:
    """Build a simple VC-style PDF document."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    title = _txt(memo.title) or "Investment memo"
    pdf.multi_cell(0, 9, title)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    meta = []
    if startup:
        meta.append(_txt(startup.name))
    meta.append(f"Status: {_txt(memo.status)}")
    meta.append(f"Generated: {memo.created_at.isoformat()[:19]}Z")
    pdf.multi_cell(0, 5, " · ".join(meta))
    pdf.ln(4)

    for heading, attr in _SECTIONS:
        body = _txt(getattr(memo, attr, None))
        if not body:
            continue
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, heading)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, body)
        pdf.ln(3)

    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode("latin-1", errors="replace")

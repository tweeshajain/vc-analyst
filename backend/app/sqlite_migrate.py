"""Lightweight SQLite column additions for evolving schemas (no Alembic)."""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_startup_radar_columns(engine: Engine) -> None:
    """Add radar / engagement columns to `startups` if missing."""
    with engine.begin() as conn:
        raw = conn.execute(text("PRAGMA table_info(startups)"))
        cols = {row[1] for row in raw.fetchall()}
        statements: list[str] = []
        if "url" not in cols:
            statements.append("ALTER TABLE startups ADD COLUMN url TEXT DEFAULT ''")
        if "source" not in cols:
            statements.append(
                "ALTER TABLE startups ADD COLUMN source TEXT DEFAULT 'manual'"
            )
        if "external_id" not in cols:
            statements.append("ALTER TABLE startups ADD COLUMN external_id TEXT")
        if "upvotes" not in cols:
            statements.append("ALTER TABLE startups ADD COLUMN upvotes INTEGER DEFAULT 0")
        if "comments_count" not in cols:
            statements.append(
                "ALTER TABLE startups ADD COLUMN comments_count INTEGER DEFAULT 0"
            )
        if "radar_score" not in cols:
            statements.append(
                "ALTER TABLE startups ADD COLUMN radar_score REAL DEFAULT 0.0"
            )
        for sql in statements:
            conn.execute(text(sql))

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_startups_radar_score "
                "ON startups (radar_score DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_startups_source_external "
                "ON startups (source, external_id) "
                "WHERE external_id IS NOT NULL AND external_id != ''"
            )
        )


def ensure_memo_structure_columns(engine: Engine) -> None:
    """Add structured memo section columns to `investment_memos` if missing."""
    with engine.begin() as conn:
        raw = conn.execute(text("PRAGMA table_info(investment_memos)"))
        cols = {row[1] for row in raw.fetchall()}
        alters: list[str] = []
        if "company_overview" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN company_overview TEXT DEFAULT ''"
            )
        if "market_opportunity" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN market_opportunity TEXT DEFAULT ''"
            )
        if "business_model" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN business_model TEXT DEFAULT ''"
            )
        if "competitive_landscape" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN competitive_landscape TEXT DEFAULT ''"
            )
        if "differentiation_analysis" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN differentiation_analysis TEXT DEFAULT ''"
            )
        if "competitive_strengths" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN competitive_strengths TEXT DEFAULT ''"
            )
        if "competition" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN competition TEXT DEFAULT ''"
            )
        if "risks" not in cols:
            alters.append("ALTER TABLE investment_memos ADD COLUMN risks TEXT DEFAULT ''")
        if "investment_thesis" not in cols:
            alters.append(
                "ALTER TABLE investment_memos ADD COLUMN investment_thesis TEXT DEFAULT ''"
            )
        for sql in alters:
            conn.execute(text(sql))


def ensure_pipeline_runs_table(engine: Engine) -> None:
    """Create `pipeline_runs` if missing (SQLite)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    finished_at DATETIME,
                    status TEXT DEFAULT 'running',
                    trigger TEXT DEFAULT 'api',
                    stats_json TEXT DEFAULT '{}',
                    error_message TEXT
                )
                """
            )
        )


def ensure_top_startups_snapshots_table(engine: Engine) -> None:
    """Create `top_startups_snapshots` if missing."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS top_startups_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    pipeline_run_id INTEGER REFERENCES pipeline_runs(id),
                    entries_json TEXT DEFAULT '[]'
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_top_startups_snapshots_captured "
                "ON top_startups_snapshots (captured_at DESC)"
            )
        )

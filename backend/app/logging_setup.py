"""Application logging: console + rotating file under `data/logs/`."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG = logging.getLogger("ai_vc_analyst")


def setup_logging() -> None:
    """Idempotent configuration for `ai_vc_analyst` loggers."""
    if getattr(_LOG, "_ai_vc_configured", False):
        return

    root_project = Path(__file__).resolve().parents[2]
    log_dir = root_project / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    _LOG.setLevel(logging.DEBUG)
    _LOG.addHandler(file_handler)
    _LOG.addHandler(console)

    pipeline = logging.getLogger("ai_vc_analyst.pipeline")
    pipeline.setLevel(logging.DEBUG)

    deals = logging.getLogger("ai_vc_analyst.deals")
    deals.setLevel(logging.INFO)

    _LOG._ai_vc_configured = True  # type: ignore[attr-defined]

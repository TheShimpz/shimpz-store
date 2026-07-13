import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.db import engine
from app.schemas import Health

router = APIRouter()
log = structlog.get_logger()


@router.get("/health", response_model=Health)
def health() -> Health:
    # Health MUST touch the DB. pool_pre_ping defers a dead/wrong DSN past startup, so a health
    # that skips the DB reports "ok" while every real request 500s (the laudoctor silent-lead-loss
    # failure). This SELECT 1 is what makes the shimpz-app post-deploy smoke gate actually bite.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.debug("health_check")
    return Health(status="ok")

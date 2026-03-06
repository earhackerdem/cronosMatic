from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.db.engine import engine
from app.schemas.health import StatusResponse

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    result: dict[str, str] = {"status": "ok"}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["database"] = "connected"
    except Exception:
        result["status"] = "degraded"
        result["database"] = "unavailable"
    return result


@router.get("/status", response_model=StatusResponse)
async def status() -> dict:
    return {
        "status": "ok",
        "message": "API is running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

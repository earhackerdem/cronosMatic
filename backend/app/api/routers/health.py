from fastapi import APIRouter
from sqlalchemy import text

from app.db.engine import engine

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

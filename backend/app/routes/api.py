from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Standard application health check.
    """
    return {
        "status": "healthy",
        "service": "Smart IT Helpdesk API",
        "version": "1.0.0"
    }


@router.get("/health/db", tags=["Health"])
def database_health_check(db: Session = Depends(get_db)):
    """
    Database connectivity check using FastAPI dependency injection.
    Safely executes a SELECT 1 ping against the database.
    """
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "connected" if result == 1 else "unexpected_result",
            "database": "PostgreSQL",
            "ping": result
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "database": "PostgreSQL",
            "error": str(e)
        }


@router.get("/api/v1", tags=["API Root"])
async def api_v1_root():
    return {
        "message": "Welcome to Smart IT Helpdesk Management API v1",
        "docs_url": "/docs",
        "status": "operational"
    }

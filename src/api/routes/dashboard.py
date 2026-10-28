"""Dashboard statistics endpoint for VeriAI."""

from fastapi import APIRouter
from src.api.database import get_dashboard_stats
from src.api.schemas import DashboardStatsResponse

router = APIRouter(prefix="/stats", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_stats():
    """Computes real-time dashboard analytics derived strictly from persisted SQLite records."""
    return get_dashboard_stats()

from fastapi import APIRouter

from app.api.v1.endpoints import intake, scorecards

api_router = APIRouter()
api_router.include_router(intake.router, prefix="/screening", tags=["screening"])
api_router.include_router(scorecards.router, prefix="/scorecards", tags=["scorecards"])

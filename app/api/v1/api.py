from fastapi import APIRouter

from app.api.v1.leads import router as leads_router
from app.api.v1.outreach import router as outreach_router

api_router = APIRouter()

api_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
api_router.include_router(outreach_router, prefix="/outreach", tags=["Outreach"])


@api_router.get("/health")
def health_check() -> dict:
    return {"status": "healthy"}

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.api import api_router
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Client Outreach Agent", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")

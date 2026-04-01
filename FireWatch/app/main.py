from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.detector import detector_service
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    detector_service.start()
    try:
        yield
    finally:
        detector_service.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.config import settings
from app.detector import detector_service
from app.routes import router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    detector_service.start()
    try:
        yield
    finally:
        detector_service.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.config.settings import Settings
from app.logging_setup import configure_logging
from app.database import init_db, close_db

configure_logging()
logger = structlog.get_logger(__name__)

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("application_starting")
    settings.validate_required()

    from app.services.browser import BrowserService
    from app.services.gemini import NvidiaService
    from app.services.telegram import TelegramService
    from app.services.scheduler import SchedulerService

    browser = BrowserService(settings)
    nvidia = NvidiaService(settings)
    telegram = TelegramService(settings)
    scheduler = SchedulerService(settings, browser, nvidia, telegram)

    app.state.browser = browser
    app.state.nvidia = nvidia
    app.state.telegram = telegram
    app.state.scheduler = scheduler
    app.state._settings = settings

    init_db()
    logger.info("database_initialized")

    await browser.start()
    scheduler.start()

    yield

    # C++ engine is managed via systemd — no subprocess to stop here

    await scheduler.stop()
    await browser.stop()
    close_db()
    logger.info("application_stopped")


app = FastAPI(
    title="Signal Notifier",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.charts import router as charts_router
from app.routes.analyses import router as analyses_router
from app.routes.notifications import router as notifications_router
from app.routes.settings import router as settings_router
from app.routes.strategy import router as strategy_router
from app.routes.trigger import router as trigger_router
from app.routes.cpp_engine import router as cpp_engine_router

app.include_router(auth_router)
app.include_router(cpp_engine_router, dependencies=[Depends(get_current_user)])
app.include_router(trigger_router)
app.include_router(dashboard_router, dependencies=[Depends(get_current_user)])
app.include_router(charts_router, dependencies=[Depends(get_current_user)])
app.include_router(analyses_router, dependencies=[Depends(get_current_user)])
app.include_router(notifications_router, dependencies=[Depends(get_current_user)])
app.include_router(settings_router, dependencies=[Depends(get_current_user)])
app.include_router(strategy_router, dependencies=[Depends(get_current_user)])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "interval_seconds": settings.CHECK_INTERVAL_SECONDS,
        "threshold": settings.NOTIFICATION_THRESHOLD,
    }

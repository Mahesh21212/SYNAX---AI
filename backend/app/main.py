"""SYNAX AI — FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .routers import chat, conversations, documents, health, memory, models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("synax")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await db.connect()
    except Exception as exc:  # keep the API up so /health can report the problem
        logger.error("MongoDB connection failed: %s", exc)
    if not settings.openrouter_configured:
        logger.warning(
            "OPENROUTER_API_KEY is not set — chat requests will fail until it is."
        )
    yield
    await db.disconnect()


app = FastAPI(
    title="SYNAX AI",
    description=(
        "Multi-agent AI workspace: a planner, specialists, a critic and a "
        "synthesizer working one request."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(memory.router)
app.include_router(models.router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {
        "name": "SYNAX AI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

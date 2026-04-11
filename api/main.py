"""
API REST Diretto — FastAPI
GNU AGPL-3.0
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import close_pool, init_pool
from .routers import companies, health, jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Diretto API",
    description="API pubblica per la piattaforma di ricerca lavoro Diretto. GNU AGPL-3.0",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# CORS — solo origini esplicitamente consentite
import os
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],      # sola lettura, nessun POST/PUT/DELETE
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router, prefix="/api")
app.include_router(companies.router, prefix="/api")

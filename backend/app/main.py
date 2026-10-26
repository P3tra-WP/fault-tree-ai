from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes_analyses, routes_health
from app.config import settings

app = FastAPI(title="fault-tree-ai")

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(routes_health.router, prefix="/api")
app.include_router(routes_analyses.router, prefix="/api")

# Serves the built Vite SPA (copied in at Docker build time). Absent in local dev when
# running the frontend separately via `npm run dev`.
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

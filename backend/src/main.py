"""
src/main.py
FastAPI application entry point.
Run with:
    uvicorn src.main:app --reload --port 8000
Or run this file directly in VS Code (Ctrl+Shift+F5) for interactive debugging.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.routers import stations, transport
import os

# App setup
app = FastAPI(
    title="Air Quality Transport API",
    description="Endpoints for station metadata, sensor data, and Gaussian plume transport matrices.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Routers
app.include_router(stations.router, prefix="/stations", tags=["Stations"])
app.include_router(transport.router, prefix="/transport", tags=["Transport Matrix"])
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")


@app.get("/", tags=["Health"])
def root():
    """Health-check endpoint."""
    return {"status": "ok", "message": "Air Quality API is running."}


# Dev entrypoint — allows `python -m backend.main` or VS Code Run/Debug
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )

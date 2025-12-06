# app/api/main.py - FULL WORKING VERSION
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

app = FastAPI(title="ADAT API Gateway")

# CORS middleware - FIXED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now
    allow_credentials=True,
    allow_methods=["*"],  # Include OPTIONS
    allow_headers=["*"],
)

# Import routers - USING ABSOLUTE PATH
try:
    # Try absolute import first
    from app.api.routes.celeryRoute import router as celery_router
    from app.api.routes.sessionRoute import router as session_router
    from app.api.routes.resultRoute import router as results_router
except ImportError:
    try:
        # Fallback: relative import
        from .routes.celeryRoute import router as celery_router
        from .routes.sessionRoute import router as session_router
        from .routes.resultRoute import router as results_router
    except ImportError:
        # Fallback: direct import (when running from api folder)
        from routes.celeryRoute import router as celery_router
        from routes.sessionRoute import router as session_router
        from routes.resultRoute import router as results_router

# Include all routers
app.include_router(celery_router)
app.include_router(session_router)
app.include_router(results_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "ADAT API Gateway", "docs": "/docs"}
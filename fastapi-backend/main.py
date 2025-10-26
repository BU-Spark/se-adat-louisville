# main.py
# run with: uvicorn main:app --reload --port 8000
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

R_SERVICE = os.getenv("R_SERVICE", "http://localhost:8001")

app = FastAPI(title="ADAT API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EligibilityInput(BaseModel):
    # Add/rename fields to match your form payload
    project_name: str = Field(..., min_length=1)
    affordable_units: float = Field(..., ge=0.0, le=1.0)

@app.get("/api/health")
async def health():
    # Check both gateway and R service
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{R_SERVICE}/health")
        ok = r.status_code == 200
    except Exception:
        ok = False
    return {"gateway":"ok", "r_service":"ok" if ok else "down"}

@app.post("/api/eligibility")
async def eligibility(payload: EligibilityInput):
    """Uniform endpoint your Astro pages can call from anywhere."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{R_SERVICE}/eligibility", json=payload.model_dump())
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"R backend error: {e}")

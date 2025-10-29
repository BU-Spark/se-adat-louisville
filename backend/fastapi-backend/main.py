from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, conint, constr
import httpx

app = FastAPI(title="ADAT API Gateway")

### ---- R service base ----
R_BASE = "http://127.0.0.1:8001"  # plumber run.r uses 8001

### ---- Existing quick endpoint (keep) ----
class EligibilityInput(BaseModel):
    affordable_units: float = Field(ge=0, le=1, description="Share of units affordable, 0..1")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/eligibility")
def eligibility(inp: EligibilityInput):
    return {
        "status": "ok",
        "result": {
            "eligible": inp.affordable_units >= 0.30,
            "affordable_units": inp.affordable_units
        }
    }

### ---- Full assessment models ----
class Affordability(BaseModel):
    ami30: conint(ge=0) = 0 
    ami50: conint(ge=0) = 0
    ami60: conint(ge=0) = 0
    ami70: conint(ge=0) = 0
    ami80: conint(ge=0) = 0

class AssessmentInput(BaseModel):
    session_id: constr(min_length=1)
    project_name: constr(min_length=1)
    project_units_total: conint(gt=0)
    build_type: Optional[str] = None
    scatter: Optional[bool] = None

    address: constr(min_length=1)
    city: constr(min_length=1)
    state: constr(min_length=2, max_length=2)
    zip: constr(min_length=5, max_length=10)

    affordability: Affordability

@app.post("/api/assess")
async def assess(payload: AssessmentInput):
    # 1) Geocode via R
    geo_req = {
        "address": payload.address,
        "city": payload.city,
        "state": payload.state,
        "zip": payload.zip
    }
    async with httpx.AsyncClient(timeout=30) as client:
        geo = await client.post(f"{R_BASE}/geocode", json=geo_req)
    if geo.status_code != 200:
        raise HTTPException(status_code=geo.status_code, detail=f"Geocode failed: {geo.text}")
    geo_json = geo.json()
    lat = geo_json.get("lat"); lng = geo_json.get("lng")
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Geocode returned no lat/lng")

    # 2) Block-group lookup via R
    async with httpx.AsyncClient(timeout=30) as client:
        bg = await client.post(f"{R_BASE}/bg-lookup", json={"lat": lat, "lng": lng})
    if bg.status_code != 200:
        raise HTTPException(status_code=bg.status_code, detail=f"BG lookup failed: {bg.text}")
    gisjoin = bg.json().get("gisjoin")
    if not gisjoin:
        raise HTTPException(status_code=404, detail="No GISJOIN found for point")

    # 3) Summarize affordable units
    total_aff = sum([
        payload.affordability.ami30,
        payload.affordability.ami50,
        payload.affordability.ami60,
        payload.affordability.ami70,
        payload.affordability.ami80
    ])
    if total_aff > payload.project_units_total:
        raise HTTPException(status_code=400, detail="affordability exceeds total units")

    # 4) Call R /assess with a compact body (mirrors your plumber /assess)
    r_body = {
        "session_id": payload.session_id,
        "project_name": payload.project_name,
        "project_units_total": payload.project_units_total,
        "affordability": jsonable_encoder(payload.affordability),
        "lat": lat,
        "lng": lng,
        "gisjoin": gisjoin
    }
    if payload.build_type is not None:
        r_body["build_type"] = payload.build_type
    async with httpx.AsyncClient(timeout=60) as client:
        r_resp = await client.post(f"{R_BASE}/assess", json=r_body)

    if r_resp.status_code != 200:
        raise HTTPException(status_code=r_resp.status_code, detail=f"R assess failed: {r_resp.text}")

    return r_resp.json()

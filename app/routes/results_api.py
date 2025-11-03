from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os
from datetime import datetime
import httpx

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")

# Create router instead of app
router = APIRouter()


# Response models
class Location(BaseModel):
    lat: float
    lng: float
    gisjoin: str


class Totals(BaseModel):
    units: int
    affordable: float


class Decision(BaseModel):
    eligible: bool
    reason: str


class AssessmentResult(BaseModel):
    session_id: str
    project_name: str
    location: Location
    totals: Totals
    decision: Decision


class AssessResponse(BaseModel):
    status: str = "ok"
    result: AssessmentResult


class ErrorResponse(BaseModel):
    status: str = "error"
    reason: str


@router.get("/storage")
async def get_assessment_results(session_id: float = Query(..., description="Session ID")):
    """
    Get assessment results from database by session_id.
    """
    
    url = SUPABASE_URL.rstrip('/') + f'/rest/v1/tool_results?session_id=eq.{int(session_id)}'
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
    }
    
    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public':
        headers['Content-Profile'] = SUPABASE_SCHEMA
        headers['Accept-Profile'] = SUPABASE_SCHEMA
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            return ErrorResponse(status="error", reason=str(e))
    
    if resp.status_code >= 400:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        return ErrorResponse(status="error", reason=str(detail))
    
    try:
        results = resp.json()
    except Exception:
        return ErrorResponse(status="error", reason="Failed to parse response")
    
    if not results or len(results) == 0:
        return ErrorResponse(status="error", reason="No results found for this session")
    
    result_data = results[0]
    
    return AssessResponse(
        status="ok",
        result=AssessmentResult(**result_data)
    )
from fastapi import APIRouter, Query
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import os
import httpx
from uuid import UUID
from typing import Optional, Dict

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        "Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    )
    
router = APIRouter()

# response models --> dummy data shape for proof of concept only, will be changed
class Affordability(BaseModel):
    ami30: Optional[int] = None
    ami50: Optional[int] = None
    ami60: Optional[int] = None
    ami70: Optional[int] = None
    ami80: Optional[int] = None


class AssessmentResult(BaseModel):
    session_id: str
    project_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    building_type: Optional[str] = None
    project_units_total: Optional[int] = None
    affordability: Optional[Affordability] = None
    developable: Optional[str] = None  # "YES" or "NO"
    
    # Allow any extra fields from the JSONB
    class Config:
        extra = "allow"


class AssessResponse(BaseModel):
    status: str = "ok"
    result: AssessmentResult


class ErrorResponse(BaseModel):
    status: str = "error"
    reason: str


# GET route
@router.get("/storage")
async def get_assessment_results(
    session_id: str = Query(
        "550e8400-e29b-41d4-a716-446655440000",
        description="Session ID (UUID)",
    )
):
    """Get assessment results from database by session_id."""

    # uuid validation
    try:
        UUID(session_id)
    except ValueError:
        return ErrorResponse(status="error", reason="Invalid UUID format for session_id")

    # supabase url
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/tool_results?session_id=eq.{session_id}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != "public":
        headers["Content-Profile"] = SUPABASE_SCHEMA
        headers["Accept-Profile"] = SUPABASE_SCHEMA

    # fetching from supabase
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            return ErrorResponse(status="error", reason=f"Request error: {str(e)}")

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except (ValueError, httpx.ResponseNotRead):
            detail = resp.text
        return ErrorResponse(status="error", reason=str(detail))

    # parsing through json
    try:
        results = resp.json()
    except (ValueError, httpx.ResponseNotRead):
        return ErrorResponse(status="error", reason="Failed to parse response")

    if not results:
        return ErrorResponse(status="error", reason="No results found for this session")

    row = results[0]
    result_data = row.get("results", {}) or {}

    
    result_data["session_id"] = row.get("session_id", session_id)
    result_data["developable"] = row.get("developable", "NO")

    try:
        result = AssessmentResult(**result_data)
    except ValidationError as e:
        return ErrorResponse(status="error", reason=f"Validation failed: {e!s}")

    return AssessResponse(status="ok", result=result)

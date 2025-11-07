from fastapi import APIRouter, Query
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import httpx
from uuid import UUID

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")

router = APIRouter()


# --- Response models ---
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


# --- GET route ---
@router.get("/storage")
async def get_assessment_results(
    session_id: str = Query(
        "550e8400-e29b-41d4-a716-446655440000",
        description="Session ID (UUID)"
    )
):
    """
    Get assessment results from database by session_id.
    """

    # 1. Validate UUID
    try:
        uuid_obj = UUID(session_id)
        session_id = str(uuid_obj)  # ensures canonical UUID format
    except ValueError:
        return ErrorResponse(status="error", reason="Invalid UUID format for session_id")

    # 2. Build Supabase REST URL
    # Note: for UUID equality in PostgREST, no quotes are needed around UUID
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/tool_results?session_id=eq.{session_id}"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    # 3. Include schema headers if not public
    if SUPABASE_SCHEMA != "public":
        headers["Content-Profile"] = SUPABASE_SCHEMA
        headers["Accept-Profile"] = SUPABASE_SCHEMA

    # 4. Fetch from Supabase
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            return ErrorResponse(status="error", reason=f"Request error: {str(e)}")

    # 5. Handle HTTP errors
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        return ErrorResponse(status="error", reason=str(detail))

    # 6. Parse JSON response
    try:
        results = resp.json()
    except Exception:
        return ErrorResponse(status="error", reason="Failed to parse JSON from Supabase")

    # 7. Check if results exist
    if not results:
        return ErrorResponse(status="error", reason="No results found for this session")

    row = results[0]

    # 8. Merge session_id with the JSONB results
    result_data = row.get("results", {})
    result_data["session_id"] = row["session_id"]

    # 9. Return as Pydantic model
    try:
        return AssessResponse(status="ok", result=AssessmentResult(**result_data))
    except Exception as e:
        return ErrorResponse(status="error", reason=f"Failed to parse result into model: {str(e)}")

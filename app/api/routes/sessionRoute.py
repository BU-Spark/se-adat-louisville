from fastapi import APIRouter, HTTPException, status  # CHANGED: was FastAPI
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any
from dotenv import load_dotenv
import os
from uuid import UUID
from datetime import datetime
import httpx

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment or .env file")

router = APIRouter()  # CHANGED: was app = FastAPI(...)

# REMOVED: CORS middleware (now in main.py)

class SessionIn(BaseModel):
    session_id: UUID = Field(..., alias="sessionID", json_schema_extra={"example": "3fa85f64-5717-4562-b3fc-2c963f66afa6"})
    created_at: datetime = Field(..., alias="createdAt", json_schema_extra={"example": "2025-10-30T12:00:00Z"})
    expires_by: datetime = Field(..., alias="expiresBy", json_schema_extra={"example": "2025-10-30T13:00:00Z"})
    is_active: bool = Field(..., alias="isActive", json_schema_extra={"example": True})

    @model_validator(mode="after")
    def check_times(self):
        if self.created_at and self.expires_by and self.expires_by <= self.created_at:
            raise ValueError("expires_by must be after created_at")
        return self

    model_config = {
        "populate_by_name": True,
    }


# REMOVED: @app.get("/health") - now in main.py


@router.post("/api/sessions", status_code=201)  # CHANGED: was @app.post
async def create_session(payload: SessionIn):
    """Async insert into Supabase using the REST endpoint (async httpx client)."""

    url = SUPABASE_URL.rstrip('/') + '/rest/v1/sessions'
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }

    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public':
        headers['Content-Profile'] = SUPABASE_SCHEMA
        headers['Accept-Profile'] = SUPABASE_SCHEMA

    payload_json = payload.model_dump(by_alias=False, exclude_none=True)
    for k, v in list(payload_json.items()):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                payload_json[k] = v.isoformat() + "Z"
            else:
                s = v.isoformat()
                payload_json[k] = s.replace("+00:00", "Z")
        elif isinstance(v, UUID):
            payload_json[k] = str(v)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=[payload_json])
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    if resp.status_code >= 400:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    try:
        inserted = resp.json()
    except Exception:
        inserted = resp.text

    return {"success": True, "result": inserted}


class AdminIn(BaseModel):
    session_id: UUID = Field(..., alias="sessionID", json_schema_extra={"example": "3fa85f64-5717-4562-b3fc-2c963f66afa6"})
    created_at: datetime = Field(..., alias="createdAt", json_schema_extra={"example": "2025-10-30T12:00:00Z"})
    expires_by: Optional[datetime] = Field(None, alias="expiresBy", json_schema_extra={"example": "2025-10-30T13:00:00Z"})
    city_information: Optional[Any] = Field(None, alias="cityInformation", json_schema_extra={"example": "Louisville, KY"})

    model_config = {"populate_by_name": True}


@router.post("/api/admin", status_code=201)  # CHANGED: was @app.post
async def create_admin(payload: AdminIn):
    """Insert a minimal admin record into the Supabase `admin` table."""

    url = SUPABASE_URL.rstrip('/') + '/rest/v1/admin'
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }

    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public':
        headers['Content-Profile'] = SUPABASE_SCHEMA
        headers['Accept-Profile'] = SUPABASE_SCHEMA

    payload_json = payload.model_dump(by_alias=False, exclude_none=True)
    for k, v in list(payload_json.items()):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                payload_json[k] = v.isoformat() + "Z"
            else:
                s = v.isoformat()
                payload_json[k] = s.replace("+00:00", "Z")
        elif isinstance(v, UUID):
            payload_json[k] = str(v)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=[payload_json])
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    if resp.status_code >= 400:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    try:
        inserted = resp.json()
    except Exception:
        inserted = resp.text

    return {"success": True, "result": inserted}
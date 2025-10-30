from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, root_validator
from typing import Optional
from dotenv import load_dotenv
import os
from uuid import UUID
from datetime import datetime

import httpx

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment or .env file")

app = FastAPI(title="ADAT FastAPI (Supabase) API")


class SessionIn(BaseModel):
    # Accept both snake_case and camelCase payloads via aliases
    session_id: UUID = Field(..., alias="sessionID", example="3fa85f64-5717-4562-b3fc-2c963f66afa6")
    created_at: datetime = Field(..., alias="createdAt", example="2025-10-30T12:00:00Z")
    expires_by: datetime = Field(..., alias="expiresBy", example="2025-10-30T13:00:00Z")
    is_active: bool = Field(..., alias="isActive", example=True)

    @root_validator
    def check_times(cls, values):
        created = values.get("created_at")
        expires = values.get("expires_by")
        if created and expires and expires <= created:
            raise ValueError("expires_by must be after created_at")
        return values

    class Config:
        allow_population_by_field_name = True


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/sessions", status_code=201)
async def create_session(payload: SessionIn):
    """Async insert into Supabase using the REST endpoint (async httpx client).

    The endpoint expects the following fields (either snake_case or camelCase):
      - session_id / sessionID (UUID)
      - created_at / createdAt (ISO 8601 timestamp with timezone)
      - expires_by / expiresBy (ISO 8601 timestamp with timezone)
      - is_active / isActive (boolean)
    """

    url = SUPABASE_URL.rstrip('/') + '/rest/v1/sessions'
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        # return the inserted row(s) in the response
        'Prefer': 'return=representation',
    }

    # Use the model's field names (snake_case) when sending to Supabase
    payload_json = payload.dict(by_alias=False, exclude_none=True)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=[payload_json])
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    if resp.status_code >= 400:
        # pass through error details when possible
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

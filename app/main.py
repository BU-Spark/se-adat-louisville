from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from typing import Optional
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

app = FastAPI(title="ADAT FastAPI (Supabase) API")


class SessionIn(BaseModel):
    # Accept both snake_case and camelCase payloads via aliases
    session_id: UUID = Field(..., alias="sessionID", json_schema_extra={"example": "3fa85f64-5717-4562-b3fc-2c963f66afa6"})
    created_at: datetime = Field(..., alias="createdAt", json_schema_extra={"example": "2025-10-30T12:00:00Z"})
    expires_by: datetime = Field(..., alias="expiresBy", json_schema_extra={"example": "2025-10-30T13:00:00Z"})
    is_active: bool = Field(..., alias="isActive", json_schema_extra={"example": True})

    @model_validator(mode="after")
    def check_times(self):
        # run after model creation so we have typed attributes available
        if self.created_at and self.expires_by and self.expires_by <= self.created_at:
            raise ValueError("expires_by must be after created_at")
        return self

    # Pydantic v2 configuration: allow population by field name so the endpoint
    # accepts either snake_case (field names) or the provided aliases (camelCase).
    model_config = {
        "populate_by_name": True,
    }


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

    # Use the standard REST path and, when a non-public schema is requested,
    # instruct PostgREST/Supabase to operate against that schema via the
    # Content-Profile / Accept-Profile headers. This avoids schema-qualification
    # in the URL which can produce cache lookup issues.
    url = SUPABASE_URL.rstrip('/') + '/rest/v1/sessions'
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        # return the inserted row(s) in the response
        'Prefer': 'return=representation',
    }

    # When a custom schema is set, tell Supabase/PostgREST which schema to use
    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public':
        headers['Content-Profile'] = SUPABASE_SCHEMA
        headers['Accept-Profile'] = SUPABASE_SCHEMA

    # Use the model's field names (snake_case) when sending to Supabase
    # Ensure any datetimes are serialized to ISO-8601 strings because
    # the httpx client/json encoder cannot serialize datetime objects.
    payload_json = payload.model_dump(by_alias=False, exclude_none=True)
    for k, v in list(payload_json.items()):
        # convert datetimes to ISO strings and UUIDs to strings so JSON serialization
        # works when httpx encodes the request body
        if isinstance(v, datetime):
            # Prefer 'Z' for UTC when possible
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

import os
import uuid
import datetime
import sys

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import httpx


from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")


if not SUPABASE_URL or not SUPABASE_KEY:
    pytest.skip("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY not set; skipping integration test.", allow_module_level=True)


from app.sessionRoute import app  # import after env check so the module-level runtime check passes


def test_post_admin_and_optional_cleanup():
    client = TestClient(app)

    session_id = str(uuid.uuid4())
    # Use a timezone-aware UTC timestamp (avoid deprecated utcnow()) and
    # format so the string ends with 'Z' for compatibility with the API.
    created_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Send the session identifier using the API's accepted alias (sessionID);
    # the backend will map it to the DB column `id` when necessary.
    # Add expiresBy and cityInformation so the admin record includes expiry
    # and location metadata.
    expires_by = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    city_information = "Louisville, KY"

    payload = {
        "sessionID": session_id,
        "createdAt": created_at,
        "expiresBy": expires_by,
        "cityInformation": city_information,
    }
    # Sanity-check the target table/column via Supabase REST before calling
    # the local API. This gives a clearer failure message when the table or
    # expected column isn't present in the PostgREST schema cache.
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != "public":
        headers["Content-Profile"] = SUPABASE_SCHEMA
        headers["Accept-Profile"] = SUPABASE_SCHEMA

    probe_url = SUPABASE_URL.rstrip("/") + "/rest/v1/admin?select=session_id&limit=1"
    probe = httpx.get(probe_url, headers=headers, timeout=10.0)
    if probe.status_code >= 400:
        # Surface the PostgREST error to make debugging easier.
        detail = None
        try:
            detail = probe.json()
        except Exception:
            detail = probe.text
        pytest.fail(
            f"Supabase schema probe failed ({probe.status_code}).\n"
            f"Response: {detail}\n\n"
            "Possible causes: the `admin` table is missing in the targeted schema, "
            "the primary key column has a different name (expected `id`), or SUPABASE_SCHEMA is set incorrectly."
        )

    # Now call the local API which forwards the insert to Supabase.
    resp = client.post("/api/admin", json=payload)
    if resp.status_code != 201:
        # Add the downstream Supabase error body to the assertion message
        msg = None
        try:
            msg = resp.json()
        except Exception:
            msg = resp.text
        pytest.fail(f"POST /api/admin failed: {resp.status_code} - {msg}")

    body = resp.json()
    assert body.get("success") is True

    result = body.get("result")
    assert isinstance(result, list) and len(result) >= 1
    inserted = result[0]

    # Supabase returns snake_case columns by default
    # The DB uses `session_id` as the column name for the primary key
    assert inserted.get("session_id") == session_id
    # Verify the extra fields were stored. Datetime formatting from PostgREST
    # may return '+00:00' instead of 'Z' for UTC; parse both sides to
    # timezone-aware datetimes and compare equality.
    def _parse_iso(s: str):
        if s is None:
            return None
        # normalize the 'Z' literal to an offset for fromisoformat
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))

    assert _parse_iso(inserted.get("expires_by")) == _parse_iso(expires_by)
    # city_information may be returned as string or JSON depending on column type
    assert str(inserted.get("city_information")) == city_information

    # Optional cleanup: delete the inserted row from the `admin` table
    # Temporarily disable automatic cleanup so inserted rows remain in
    # Supabase for manual inspection. Set SUPABASE_TEST_AUTOCLEANUP=1 to
    # re-enable automatic deletion.
    auto_cleanup = os.getenv("SUPABASE_TEST_AUTOCLEANUP", "0")
    if str(auto_cleanup).lower() in ("1", "true", "yes"):
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        if SUPABASE_SCHEMA and SUPABASE_SCHEMA != "public":
            headers["Content-Profile"] = SUPABASE_SCHEMA
            headers["Accept-Profile"] = SUPABASE_SCHEMA
        delete_url = SUPABASE_URL.rstrip("/") + f"/rest/v1/admin?session_id=eq.{session_id}"
        r = httpx.delete(delete_url, headers=headers, timeout=10.0)
        assert r.status_code in (200, 204), f"Cleanup delete failed: {r.status_code} {r.text}"
    else:
        # Print a curl command the developer can run to delete the row manually
        print("SUPABASE_TEST_AUTOCLEANUP is disabled; inserted row left in DB.")
        print("Run the following to remove it:")
        print(
            f"curl -X DELETE '{SUPABASE_URL.rstrip('/')}/rest/v1/admin?session_id=eq.{session_id}' -H \"apikey: {SUPABASE_KEY}\" -H \"Authorization: Bearer {SUPABASE_KEY}\" -H \"Content-Type: application/json\""
        )

"""Integration test: POST a session to the FastAPI app which inserts into Supabase.

This test will only run if `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set in the
environment (or in `.env`). It posts a generated session to the app (in-process via
TestClient), asserts the insert succeeded, and then deletes the inserted row from
Supabase so the test is idempotent.

Run locally:
  python app/tests/test_post_session.py
or via pytest:
  pytest -q app/tests/test_post_session.py
"""

import os
import sys
import uuid
import datetime
from dotenv import load_dotenv
import httpx
import pytest
from fastapi.testclient import TestClient

# Ensure the repository root is on sys.path so `from app.main import app` works
# when pytest executes tests from a different working directory.
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")

# import app after loading environment
from app.main import app
client = TestClient(app)


def make_payload() -> dict:
    sid = str(uuid.uuid4())
    # timezone-aware UTC datetimes, normalized to 'Z'
    created = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    expires = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "session_id": sid,
        "created_at": created,
        "expires_by": expires,
        "is_active": True,
    }


def run_test():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        pytest.skip("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to run integration test")

    payload = make_payload()
    print("Posting payload:", payload)

    # Post to the app in-process; the app will forward to Supabase
    r = client.post("/api/sessions", json=payload)

    print("Status:", r.status_code)
    try:
        data = r.json()
    except Exception:
        data = r.text
    print("Response:", data)

    assert r.status_code in (200, 201), f"Unexpected status: {r.status_code} - {r.text}"
    assert isinstance(data, dict), "Response is not JSON object"
    assert data.get("success") is True, f"API returned failure: {data}"
    assert isinstance(data.get("result"), list), "Expected result to be a list"
    assert len(data["result"]) >= 1, "No rows returned"

    row = data["result"][0]
    # ensure the session_id round-trips
    assert str(row.get("session_id")) == payload["session_id"], "session_id mismatch"

    # Cleanup: remove the inserted session row from Supabase so tests are idempotent
    delete_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/sessions?session_id=eq.{payload['session_id']}"
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
    }
    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public':
        headers['Content-Profile'] = SUPABASE_SCHEMA
        headers['Accept-Profile'] = SUPABASE_SCHEMA
    with httpx.Client(timeout=15.0) as hb:
        del_resp = hb.delete(delete_url, headers=headers)
    print("Cleanup status:", del_resp.status_code, del_resp.text)
    assert del_resp.status_code in (200, 204), f"Failed to delete test row: {del_resp.status_code} - {del_resp.text}"


def main() -> int:
    try:
        run_test()
    except AssertionError as e:
        print("TEST FAILED:", e)
        return 2
    except Exception as e:
        print("ERROR:", e)
        return 3
    else:
        print("TEST PASSED")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Pytest entrypoint
def test_post_session():
    """Pytest-compatible test entry that calls the runnable test helper.

    Run with `pytest app/tests/test_post_session.py` or `pytest -q`.
    """
    run_test()

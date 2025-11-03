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

_supabase_url = os.getenv("SUPABASE_URL")
SUPABASE_URL = _supabase_url.strip() if _supabase_url else None

_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SERVICE_ROLE_KEY = _supabase_key.strip() if _supabase_key else None

_supabase_schema = os.getenv("SUPABASE_SCHEMA")
SUPABASE_SCHEMA = _supabase_schema.strip() if _supabase_schema else "public"

# Control whether the test auto-deletes the inserted row. Set to 'false' to keep
# the row for inspection. Default: true (auto-cleanup).
_cleanup = os.getenv("SUPABASE_TEST_AUTOCLEANUP", "true")
SUPABASE_TEST_AUTOCLEANUP = str(_cleanup).strip().lower() in ("1", "true", "yes")

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

    # Prepare cleanup info (delete URL and headers)
    delete_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/sessions?session_id=eq.{payload['session_id']}"
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
    }
    if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public':
        headers['Content-Profile'] = SUPABASE_SCHEMA
        headers['Accept-Profile'] = SUPABASE_SCHEMA

    # If running interactively (script) give the user a prompt to inspect before deleting.
    # When running under pytest, respect SUPABASE_TEST_AUTOCLEANUP environment flag.
    running_under_pytest = 'PYTEST_CURRENT_TEST' in os.environ or 'pytest' in sys.modules

    if running_under_pytest and not SUPABASE_TEST_AUTOCLEANUP:
        # Do not auto-delete; print instructions so the developer can delete manually later.
        print("\nAutocleanup is disabled (SUPABASE_TEST_AUTOCLEANUP=false). The test row was not deleted.")
        print("Delete it manually with one of these commands:")
        print("PowerShell (Invoke-RestMethod):")
        ps_cmd = (
            f"Invoke-RestMethod -Uri \"{delete_url}\" -Method DELETE -Headers @{{\n"
            f"  'apikey' = '{SUPABASE_SERVICE_ROLE_KEY}';\n"
            f"  'Authorization' = 'Bearer {SUPABASE_SERVICE_ROLE_KEY}';\n"
            + (f"  'Content-Profile' = '{SUPABASE_SCHEMA}';\n  'Accept-Profile' = '{SUPABASE_SCHEMA}';\n" if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public' else "")
            + " }}"
        )
        print(ps_cmd)
        print("curl (bash):")
        curl_cmd = (
            f"curl -X DELETE '{delete_url}' -H \"apikey: {SUPABASE_SERVICE_ROLE_KEY}\" -H \"Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}\""
            + (f" -H \"Content-Profile: {SUPABASE_SCHEMA}\" -H \"Accept-Profile: {SUPABASE_SCHEMA}\"" if SUPABASE_SCHEMA and SUPABASE_SCHEMA != 'public' else "")
        )
        print(curl_cmd)
        return

    # Interactive path when running as script
    if not running_under_pytest:
        print("\nInserted test row. Press Enter to delete it, or Ctrl+C to keep it for inspection.")
        try:
            input()
        except KeyboardInterrupt:
            print("Skipping deletion (user requested to keep row).")
            return

    # Default auto-cleanup (either pytest with SUPABASE_TEST_AUTOCLEANUP true or user pressed Enter)
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

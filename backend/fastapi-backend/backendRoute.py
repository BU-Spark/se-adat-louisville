from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def store_session_results(session_id: str, fake_results: dict):
    """Store results in Supabase"""
    print(f"\n[BACKEND DB] Storing results for session: {session_id}")

    try:
        # STEP 1: Create/update session first (required for foreign key)
        now = datetime.now(timezone.utc)
        session_data = {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "expires_by": (now + timedelta(days=30)).isoformat(),
            "is_active": True
        }
        supabase.table("sessions").upsert(session_data).execute()
        print("[BACKEND DB] ✓ Session created/updated")

        # STEP 2: Now store tool_results (with foreign key to session)
        result_data = {
            "session_id": session_id,
            "results": fake_results,
            "developable": "YES" if fake_results.get("eligible") else "NO"
        }
        supabase.table("tool_results").upsert(result_data).execute()
        print("[BACKEND DB] ✓ Stored in tool_results table\n")

    except Exception as e:
        print(f"[BACKEND DB] ✗ Error: {e}\n")
        raise

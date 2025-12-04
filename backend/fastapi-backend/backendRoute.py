from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def store_session_results(session_id: str, results: dict):
    """Store recommendation results in Supabase"""
    if not results or not isinstance(results, dict):
        raise ValueError(f"results must be a non-empty dict, got: {type(results)}")
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

        # STEP 2: Determine developable status based on recommendation
        recommendation = results.get("recommendation", "undetermined")
        
        # Map recommendation to developable status
        if recommendation == "recommended":
            developable = "YES"
        elif recommendation == "conditional":
            developable = "CONDITIONAL"
        elif recommendation == "not_recommended":
            developable = "NO"
        else:
            developable = "UNDETERMINED"
        
        # Store tool_results (with foreign key to session)
        result_data = {
            "session_id": session_id,
            "results": results,
            "developable": developable
        }
        supabase.table("tool_results").upsert(result_data).execute()
        print(f"[BACKEND DB] ✓ Stored in tool_results table (developable: {developable})")
        print(f"[BACKEND DB] ✓ Recommendation: {recommendation}")
        print(f"[BACKEND DB] ✓ Risk level: {results.get('risk_level', 'unknown')}\n")

    except Exception as e:
        print(f"[BACKEND DB] ✗ Error: {e}\n")
        raise
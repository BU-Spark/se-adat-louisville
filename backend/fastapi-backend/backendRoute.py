from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def store_session_results(session_id: str, fake_results: dict):
    """Store results in Supabase"""
    print(f"\n[BACKEND DB] Storing results for session: {session_id}")
    
    try:
        # STEP 1: Create/update session first (required for foreign key)
        session_data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_by": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "is_active": True
        }
        supabase.table("sessions").upsert(session_data).execute()
        print(f"[BACKEND DB] ✓ Session created/updated")
        
        # STEP 2: Now store tool_results (with foreign key to session)
        result_data = {
            "session_id": session_id,
            "results": fake_results,
            "developable": "YES" if fake_results.get("eligible") else "NO"
        }
        supabase.table("tool_results").upsert(result_data).execute()
        print(f"[BACKEND DB] ✓ Stored in tool_results table\n")
        
    except Exception as e:
        print(f"[BACKEND DB] ✗ Error: {e}\n")
        raise
# celery_worker/backendRoute.py
from datetime import datetime, timedelta, timezone
from supabase import Client, create_client
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

def store_session_results(session_id: str, results: dict):
    """Store results in Supabase"""
    if not results or not isinstance(results, dict):
        raise ValueError(f"results must be a non-empty dict, got: {type(results)}")
    print(f"\n[CELERY DB] Storing results for session: {session_id}")

    # Load environment variables here
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # FIXED NAME
    
    # DEBUG: Print what was loaded
    print(f"[CELERY DB DEBUG] SUPABASE_URL loaded: {'YES' if SUPABASE_URL else 'NO'}")
    print(f"[CELERY DB DEBUG] SUPABASE_SERVICE_ROLE_KEY loaded: {'YES' if SUPABASE_SERVICE_ROLE_KEY else 'NO'}")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print(f"[CELERY DB DEBUG] Missing: URL={SUPABASE_URL}, KEY={SUPABASE_SERVICE_ROLE_KEY}")
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set")

    # WORKAROUND: Monkeypatch httpx.Client to ignore incompatible kwargs from gotrue library
    # The supabase/gotrue library has a bug where it passes incompatible kwargs to httpx.Client
    try:
        import httpx as httpx_module
        original_client_init = httpx_module.Client.__init__
        
        def patched_client_init(self, *args, **kwargs):
            """Filter out kwargs that httpx.Client doesn't accept"""
            # Remove 'proxy' and other gotrue-specific kwargs that httpx doesn't recognize
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['proxy']}
            original_client_init(self, *args, **filtered_kwargs)
        
        # Apply the patch
        httpx_module.Client.__init__ = patched_client_init
        print("[CELERY DB] Applied httpx.Client kwargs filtering workaround")
    except Exception as e:
        print(f"[CELERY DB] Warning: Could not patch httpx.Client ({e}), attempting without patch...")

    # Now create the supabase client (should work with the patch)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

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
        print("[CELERY DB] ✓ Session created/updated")

        # STEP 2: Now store tool_results (with foreign key to session)
        # Map recommendation to developable (YES = recommended, NO = not_recommended)
        is_recommended = results.get("recommendation") == "recommended"
        result_data = {
            "session_id": session_id,
            "results": results,
            "developable": "YES" if is_recommended else "NO"
        }
        supabase.table("tool_results").upsert(result_data).execute()
        print("[CELERY DB] ✓ Stored in tool_results table\n")

    except Exception as e:
        print(f"[CELERY DB] ✗ Error: {e}\n")
        raise
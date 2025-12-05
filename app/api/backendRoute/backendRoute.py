from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def store_session_results(session_id: str, fake_results: dict):
    """Store results in Supabase"""
    if not fake_results or not isinstance(fake_results, dict):
        raise ValueError(f"fake_results must be a non-empty dict, got: {type(fake_results)}")
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

# Add this at the very bottom of your backendRoute.py file
if __name__ == "__main__":
    import uvicorn
    import subprocess
    import threading
    import time
    import signal
    import sys
    
    # Start Redis locally if not running
    def check_redis():
        import redis
        try:
            r = redis.Redis.from_url(REDIS_URL)
            r.ping()
            print("✅ Redis is running")
            return True
        except:
            print("❌ Redis is not running")
            return False
    
    def start_redis():
        print("🔄 Attempting to start Redis server...")
        try:
            # For Windows
            subprocess.Popen(["redis-server"], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
            time.sleep(3)
            return check_redis()
        except:
            try:
                # Try Docker
                subprocess.run(["docker", "run", "-d", "-p", "6379:6379", 
                              "redis"], check=True)
                time.sleep(3)
                return check_redis()
            except:
                return False
    
    def start_celery():
        """Start Celery worker in a separate thread"""
        def run_celery():
            from celery.bin import worker
            worker = worker.worker(app=celery_app)
            worker.run(
                queues=['default'],
                hostname='localhost',
                concurrency=2,
                loglevel='INFO'
            )
        
        celery_thread = threading.Thread(target=run_celery, daemon=True)
        celery_thread.start()
        time.sleep(2)
        print("✅ Celery worker started")
        return celery_thread
    
    # Main execution
    print("🚀 Starting self-contained ADAT backend...")
    
    # 1. Check/setup Redis
    if not check_redis():
        if not start_redis():
            print("Please install and start Redis manually:")
            print("1. Install: https://redis.io/docs/install/")
            print("2. Run: redis-server")
            sys.exit(1)
    
    # 2. Start Celery worker
    celery_thread = start_celery()
    
    # 3. Start FastAPI server
    print("🌐 Starting FastAPI server on http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\nEndpoints:")
    print("  POST /api/assess     - Queue assessment")
    print("  GET  /api/task/{id}  - Check task status")
    print("  GET  /api/health     - Health check")
    print("\nPress Ctrl+C to stop\n")
    
    # Run FastAPI
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for self-contained
        log_level="info"
    )
from celery import Celery
import os
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise ValueError("REDIS_URL must be set in .env file")

# Use Redis as both broker and result backend
celery_app = Celery(
    "adat_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/New_York',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    result_backend_transport_options={'visibility_timeout': 3600},
)

@celery_app.task(name="process_assessment", bind=True)
def process_assessment_task(self, payload):
    """
    Celery task:
    1. Run fake R script (with timeout simulation)
    2. Send session_id + results to backend_db
    """
    try:
        from fakeScript import simulate_r_processing
        from backendRoute import store_session_results
        
        print(f"\n{'='*60}")
        print(f"[CELERY] Task {self.request.id} started")
        print(f"{'='*60}")
        
        # Step 1: Run fake R script (simulates timeout)
        fake_results = simulate_r_processing(payload)
        
        # Step 2: Store session_id + results in database
        session_id = payload.get("session_id")
        store_session_results(session_id, fake_results)
        
        print(f"{'='*60}")
        print(f"[CELERY] Task {self.request.id} completed")
        print(f"{'='*60}\n")
        
        return {
            "status": "completed",
            "task_id": self.request.id,
            "session_id": session_id,
            "results": fake_results
        }
            
    except Exception as e:
        print(f"\n[CELERY] Task failed: {str(e)}\n")
        raise
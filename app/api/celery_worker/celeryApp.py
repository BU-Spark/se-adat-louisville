# celery_worker/celeryApp.py
from celery import Celery
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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
    task_time_limit=30,
    result_expires=600,
    broker_connection_retry_on_startup=True,
)

@celery_app.task(name="process_assessment", bind=True)
def process_assessment_task(self, payload):
    """
    Real Celery task that processes assessment data
    """
    try:
        from celery_worker.backendRoute import store_session_results
        
        print(f"\n{'='*60}")
        print(f"[CELERY] Task {self.request.id} started")
        print(f"Processing payload: {payload}")
        print(f"{'='*60}")
        
        # Extract real data from payload
        affordability = payload.get("affordability", {})
        a30 = affordability.get("ami30", 0)
        a50 = affordability.get("ami50", 0)
        a60 = affordability.get("ami60", 0)
        a70 = affordability.get("ami70", 0)
        a80 = affordability.get("ami80", 0)
        total_units = payload.get("project_units_total", 0)
        
        # Calculate based on actual inputs
        total_affordable = a30 + a50 + a60 + a70 + a80
        percentage = (total_affordable / total_units * 100) if total_units > 0 else 0
        
        # Business logic: Project is eligible if >= 20% affordable units
        # You can change this threshold or add more complex logic
        eligible = percentage >= 20
        
        # Create comprehensive results
        results = {
            "eligible": eligible,
            "developable": "YES" if eligible else "NO",  # Required for frontend
            "score": round(percentage, 1),  # Score from 0-100
            "total_affordable": total_affordable,
            "percentage_affordable": round(percentage, 2),
            "total_units": total_units,
            "affordability_breakdown": {
                "ami30": a30,
                "ami50": a50,
                "ami60": a60,
                "ami70": a70,
                "ami80": a80
            },
            "processed_at": datetime.now().isoformat(),
            "session_id": payload.get("session_id", "unknown"),
            "project_name": payload.get("project_name", ""),
            "address": payload.get("address", ""),
            "city": payload.get("city", ""),
            "state": payload.get("state", ""),
            "zip": payload.get("zip", ""),
            "task_id": self.request.id
        }
        
        print(f"[CELERY] Calculated results:")
        print(f"  Total units: {total_units}")
        print(f"  Affordable units: {total_affordable}")
        print(f"  Percentage: {percentage:.1f}%")
        print(f"  Eligible: {eligible} (developable: {'YES' if eligible else 'NO'})")
        
        # Store results in database
        session_id = payload.get("session_id")
        if not session_id:
            raise ValueError("session_id is required in payload")
            
        store_session_results(session_id, results)
        
        print(f"{'='*60}")
        print(f"[CELERY] Task {self.request.id} completed")
        print(f"{'='*60}\n")
        
        return {
            "status": "completed",
            "task_id": self.request.id,
            "session_id": session_id,
            "results": results
        }
            
    except Exception as e:
        print(f"\n[CELERY] Task failed: {str(e)}\n")
        raise

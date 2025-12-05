from celery import Celery
import os
from dotenv import load_dotenv

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
    1. Run recommendation logic from app.py
    2. Send session_id + results to backend_db
    """
    try:
        from app import compute_recommendation_logic
        from backendRoute import store_session_results
        
        print(f"\n{'='*60}")
        print(f"[CELERY] Task {self.request.id} started")
        print(f"{'='*60}")
        
        # Extract required parameters from payload
        affordability = payload.get("affordability", {})
        
        # Map AMI levels to appFix parameters
        # Combine middle and upper tiers as needed
        a30 = affordability.get("ami30", 0)
        a50 = affordability.get("ami50", 0) + affordability.get("ami60", 0)
        a70 = affordability.get("ami70", 0) + affordability.get("ami80", 0)
        
        bgid = payload.get("bgid")
        proj_size = payload.get("project_units_total")
        
        print(f"[CELERY] Processing: {payload.get('project_name')}")
        print(f"[CELERY] BGID: {bgid}")
        print(f"[CELERY] Project size: {proj_size} units")
        print(f"[CELERY] Affordability: 30%AMI={a30}, 50%AMI={a50}, 70%AMI={a70}")
        
        # Step 1: Run recommendation logic
        recommendation_result = compute_recommendation_logic(
            a30=a30,
            a50=a50,
            a70=a70,
            bgid=bgid,
            proj_size=proj_size,
            adat_df=None  # Will load from file
        )
        
        # Check if recommendation was successful
        if not recommendation_result.get("success"):
            error_msg = recommendation_result.get("error", "Unknown error")
            print(f"[CELERY] ✗ Recommendation failed: {error_msg}")
            raise ValueError(f"Recommendation computation failed: {error_msg}")
        
        print(f"[CELERY] ✓ Recommendation: {recommendation_result['recommendation']}")
        print(f"[CELERY] Risk level: {recommendation_result['risk_level']}")
        
        # Step 2: Prepare results for storage
        session_id = payload.get("session_id")
        if not session_id:
            raise ValueError("session_id is required in payload")
        
        # Build comprehensive result object
        results = {
            "session_id": session_id,
            "project_name": payload.get("project_name"),
            "recommendation": recommendation_result["recommendation"],
            "risk_level": recommendation_result["risk_level"],
            "messages": recommendation_result["messages"],
            "bgid": recommendation_result["bgid"],
            "project_units_total": proj_size,
            "affordability_breakdown": {
                "ami30": a30,
                "ami50_60": a50,  # Combined
                "ami70_80": a70,  # Combined
            },
            "analysis": {
                "crit2_index": recommendation_result.get("crit2_index"),
                "share_affordable_at_crit2": recommendation_result.get("share_affordable_at_crit2"),
                "cost_burden_pct": recommendation_result.get("cost_burden_pct"),
            }
        }
        
        # Step 3: Store results in database
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

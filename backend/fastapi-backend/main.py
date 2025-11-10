from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, conint, constr
from celery.result import AsyncResult
from celeryApp import celery_app, process_assessment_task
from dotenv import load_dotenv
import uuid

load_dotenv()

app = FastAPI(title="ADAT API Gateway")

@app.get("/api/health")
def health():
    return {"status": "ok"}

### ---- Models ----
class Affordability(BaseModel):
    ami30: conint(ge=0) = 0 
    ami50: conint(ge=0) = 0
    ami60: conint(ge=0) = 0
    ami70: conint(ge=0) = 0
    ami80: conint(ge=0) = 0

class AssessmentInput(BaseModel):
    session_id: Optional[constr(min_length=1)] = None  # Make it optional
    project_name: constr(min_length=1)
    project_units_total: conint(gt=0)
    build_type: Optional[str] = None
    scatter: Optional[bool] = None
    address: constr(min_length=1)
    city: constr(min_length=1)
    state: constr(min_length=2, max_length=2)
    zip: constr(min_length=5, max_length=10)
    affordability: Affordability

### ---- Main Route - JUST receives and queues ----
@app.post("/api/assess")
async def assess(payload: AssessmentInput):
    print(f"\n[MAIN.PY] Received request for: {payload.project_name}")
    
    # Auto-generate UUID if session_id not provided or invalid
    if payload.session_id is None:
        session_id = str(uuid.uuid4())
        print(f"[MAIN.PY] Generated new session_id: {session_id}")
    else:
        try:
            # Validate it's a proper UUID
            uuid.UUID(payload.session_id)
            session_id = payload.session_id
        except ValueError:
            # If invalid UUID format, generate new one
            session_id = str(uuid.uuid4())
            print(f"[MAIN.PY] Invalid UUID provided, generated new: {session_id}")
    
    # Convert to dict for Celery
    celery_payload = {
        "session_id": session_id,  # Use validated/generated UUID
        "project_name": payload.project_name,
        "project_units_total": payload.project_units_total,
        "build_type": payload.build_type,
        "scatter": payload.scatter,
        "address": payload.address,
        "city": payload.city,
        "state": payload.state,
        "zip": payload.zip,
        "affordability": payload.affordability.dict()
    }
    
    # Queue task
    task = process_assessment_task.delay(celery_payload)
    
    print(f"[MAIN.PY] Queued task: {task.id}\n")
    
    return {
        "status": "queued",
        "message": "Assessment queued for processing",
        "task_id": task.id,
        "session_id": session_id  # Return the UUID we're using
    }

### ---- Check task status ----
@app.get("/api/task/{task_id}")
def get_task_status(task_id: str):
    """Check Celery task status"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Waiting in queue"
        }
    elif task_result.state == 'PROCESSING':
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Fake script is running"
        }
    elif task_result.state == 'SUCCESS':
        return {
            "task_id": task_id,
            "status": "completed",
            "result": task_result.result
        }
    elif task_result.state == 'FAILURE':
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(task_result.info)
        }
    else:
        return {
            "task_id": task_id,
            "status": task_result.state.lower()
        }
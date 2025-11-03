from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Import your routes
from routes.results_api import router as results_router

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment or .env file")

app = FastAPI(title="ADAT Results API")

# Include routers
app.include_router(results_router)

@app.get("/health")
async def health():
    from datetime import datetime
    return {"status": "ok", "ts": datetime.utcnow().isoformat() + "Z"}
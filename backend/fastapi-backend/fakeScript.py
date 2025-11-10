import time
from typing import Dict, Any
from datetime import datetime, timezone

def simulate_r_processing(payload: Dict[str, Any]) -> Dict[str, Any]:
    print("\n[FAKE R SCRIPT] Starting processing...")
    print(f"[FAKE R SCRIPT] Session ID: {payload.get('session_id')}")
    print(f"[FAKE R SCRIPT] Project: {payload.get('project_name')}")
    
    # Simulate R processing time (like the old R plumber service)
    print("[FAKE R SCRIPT] Processing (simulating delay)...")
    time.sleep(3)  # Simulate 3 second processing time
    
    # Calculate total affordable (this is the only real logic)
    affordability = payload.get("affordability", {})
    total_affordable = sum([
        affordability.get("ami30", 0),
        affordability.get("ami50", 0),
        affordability.get("ami60", 0),
        affordability.get("ami70", 0),
        affordability.get("ami80", 0)
    ])
    
    total_units = payload.get("project_units_total", 0)
    eligible = (total_affordable >= 0.3 * total_units)
    
    # Return simple result (like R used to)
    result = {
        "session_id": payload.get("session_id"),
        "project_name": payload.get("project_name"),
        "eligible": eligible,
        "total_affordable": total_affordable,
        "total_units": total_units,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"[FAKE R SCRIPT] Processing complete! Eligible: {eligible}\n")
    
    return result

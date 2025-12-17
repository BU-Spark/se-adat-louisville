# Analysis Application

Core displacement risk assessment logic and data access.

## Files

- **`app.py`** - Policy compliance evaluation engine
- **`dataLoader.py`** - Loads CSVs from Supabase Storage
- **`diagnoseSector.py`** - Debugging utilities for BGID lookup

## Usage
```python
from app import compute_recommendation_logic

result = compute_recommendation_logic(
    a30=10, a50=20, a70=15,  # Units at each AMI level
    proj_size=50,
    address="123 Main St", city="Louisville", state="KY"
)

# Returns: {"recommendation": "recommended"|"not_recommended", "messages": [...]}
```

## Policy Rules

- **High Risk:** ALL units affordable; critical AMI % ≥ cost-burdened %
- **Medium Risk:** Critical AMI % ≥ cost-burdened %
- **Low Risk:** ≥10% units at ≤50% AMI

## Environment
```env
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key
```

## Testing
```bash
python app.py G2100111001001 50 --a30 10 --a50 20
python diagnoseSector.py ./data/LVM_Risk_Database.csv
```

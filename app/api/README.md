# API Backend

FastAPI routes and Celery worker for asynchronous project assessments.

## Architecture

<img width="639" height="438" alt="image" src="https://github.com/user-attachments/assets/c6ea1649-6121-4f28-8ab0-0bfe104f8f61" />


## Structure
```
api/
├── routes/
│   ├── celeryRoute.py      # POST /api/assess - Submit assessment
│   ├── resultsRoute.py     # GET /storage - Retrieve results
│   └── sessionRoute.py     # Session/admin management
├── celery_worker/
│   ├── celeryApp.py         # Task definitions
│   └── backendRoute.py      # Database operations
└── tests/
    ├── test_app.py          # Recommendation logic unit tests
    ├── test_post_session.py # Session endpoint integration
    └── test_post_admin.py   # Admin endpoint integration
```

## Key Endpoints

- **POST `/api/assess`** - Queue assessment task
- **GET `/api/task/{task_id}`** - Check task status
- **GET `/storage?session_id={uuid}`** - Get results
- **POST `/api/sessions`** - Create session
- **POST `/api/admin`** - Create admin record

## Flow

1. Submit project → Returns `task_id` + `session_id`
2. Task queued in Redis → Celery worker processes
3. Results stored in Supabase → Poll or retrieve by session_id

## Running
```bash
# Terminal 1: API
uvicorn app.api.main:app --reload --port 8000

# Terminal 2: Celery Worker
celery -A app.api.celery_worker.celeryApp worker --loglevel=info --pool=solo

# Terminal 3: Redis (if not using Docker)
redis-server
```

## Environment
```env
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key
REDIS_URL=redis://localhost:6379/0
```

## Request Example
```json
POST /api/assess
{
  "project_name": "Affordable Housing",
  "project_units_total": 50,
  "address": "123 Main St",
  "city": "Louisville",
  "state": "KY",
  "zip": "40202",
  "affordability": {"ami30": 10, "ami50": 20, "ami60": 10}
}

Response: {"status": "queued", "task_id": "...", "session_id": "..."}
```

## Testing
```bash
# All tests
pytest app/tests/

# Unit tests only (no database)
pytest app/tests/test_app.py

# Keep test data
SUPABASE_TEST_AUTOCLEANUP=false pytest app/tests/test_post_session.py
```

## Troubleshooting

- **Tasks not processing**: Check `REDIS_URL` connection
- **Results not storing**: Verify `SUPABASE_SERVICE_ROLE_KEY` (not anon key)
- **Windows Celery issues**: Use `--pool=solo` flag

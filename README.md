## Overview
ADAT (Anti-Displacement Assessment Tool) evaluates proposed affordable housing developments by analyzing project details—location, size, and affordability mix—against 14 demographic and economic indicators to calculate neighborhood displacement risk. Based on this risk and local policy rules, it recommends whether projects should be supported. The system is designed with abstraction in mind, allowing other cities to implement their own assessment logic.

**Key Capabilities:**
- Automated displacement risk assessment for Louisville neighborhoods
- Policy-based project evaluation with additional reasoning
- Affordability requirement enforcement based on area, with stricter rules for higher-risk areas

## Technical Architecture
<img width="1100" height="443" alt="image" src="https://github.com/user-attachments/assets/a5e43037-bb57-4c4e-860c-a97e5d1174db" />

### Architecture Diagram

### Tech Stack
- **Frontend:** Astro, React, Tailwind CSS → Next.js
- **Backend:** FastAPI, Celery, Redis (Upstash)
- **Database:** Supabase (PostgreSQL + storage)
- **Data Pipeline:** Python, Pandas, GeoPandas, NHGIS census data
- **Infrastructure:** Docker Compose (local), Production TBD

## How to Run

### Prerequisites
- **Docker & Docker Compose** – for running the full stack locally
- **Python 3.11+** – required for backend, ETL, and tests
- **Node.js 20+ & npm** – required for frontend (Astro/React)
- **Git** – to clone the repository and manage branches
- **Google Maps API key** – for map features in the frontend
- Optional for local ETL: 4GB+ RAM recommended due to geospatial processing with GeoPandas and Shapely

### Quick Start with Docker Compose
```bash
# Clone the repository
git clone https://github.com/BU-Spark/se-adat-louisville
cd se-adat-louisville

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Build Docker image and start all services
docker-compose up --build
```
### Manual Setup (Alternative)
Instructions for running each component individually (link to component READMEs)

#### ETL Setup
For details on the ETL pipeline, see the [Pipeline README](pipeline/README.md).

#### Analysis App Setup
For details on the App Setup, see the [Services README](app/services/README.md).

#### API Setup
For details on the API Setup, see the [API README](app/api/README.md).

#### Frontend Setup
For details on the API Setup, see the [Frontend README](src/README.md).

## Environment Variables
List of required environment variables across all components:

+### Supabase (get from `https://app.supabase.com/project/ttbbmlochycxvdbfxynp/settings/api`)
+```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```
### Redis (use this exact value for Docker)
```
REDIS_URL=redis://redis:6379/0
```

## Known Issues and Bugs

- **Celery on Windows:** Celery may fail to start on Windows without using the `--pool=solo` flag.

- **Supabase permissions:** API tasks and integration tests require a Supabase **service role key**; using an anon key will cause write operations to fail.

- **Redis dependency:** If Redis is not running or misconfigured, asynchronous assessments will not process.

- **Incomplete extracted data:** Some fields in the extracted displacement risk database contain missing values due to gaps in historical census data.

- **Frontend deployment:** The frontend is not yet deployed; API URLs and environment variables may require adjustment for production.


## Deployment
**Current Status:** Local development only - not deployed to production. This project is designed to run via Docker Compose on any machine. See the Getting started section for complete setup instructions.

**Recommended platforms:**
- Frontend: Vercel, Netlify
- Backend: Railway, Render, AWS
- Database: Supabase (production instance)

## Development

### Running Tests
Automated tests are implemented for the **API backend**, including unit tests for recommendation logic and integration tests for Supabase-backed endpoints.

To run tests, follow the instructions in the **API README**:

**`app/api/README.md` → testing section**

### Project Structure
```
├── pipeline/              # ETL / data processing pipeline
├── app/
│   ├── api/              # FastAPI backend & Celery worker
│   └── services/         # Analysis application & policy logic
├── src/                  # Frontend application (Astro + React + Tailwind)
├── CI/                   # Continuous Integration configuration (GitHub Actions)
├── docker-compose.yml    # Local development orchestration
├── .env.example          # Template environment variables
└── README.md             # Main project overview and instructions
```

## Team Members
- Ramona Bergeron
- Daniel Kryzhanovsky
- Jen (Jenny) Tang

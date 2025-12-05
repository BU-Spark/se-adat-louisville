# CI Pipeline - README

## Project Overview
This project is an ADAT (Affordable Development Assessment Tool) API that processes housing development assessments using FastAPI, Celery, and Supabase. The application consists of a Python backend with asynchronous task processing and a TypeScript/Astro frontend.

## CI Tool Used
**GitHub Actions**

GitHub Actions was selected as the CI/CD platform because:
- Native integration with GitHub repositories
- Free for public repositories and generous limits for private repos
- Extensive marketplace of pre-built actions
- Support for matrix builds across multiple Python and Node.js versions
- Easy configuration using YAML syntax

## Tasks Implemented

### 1. Code Linting ✓
**Python Backend:**
- **Flake8**: Enforces PEP 8 style guide compliance
- **Black**: Automatic code formatting check
- Configuration: Maximum line length of 88 characters (Black default)

**TypeScript/JavaScript Frontend:**
- **ESLint**: Enforces TypeScript and React best practices
- **Prettier**: Code formatting validation
- Configuration: Standard React/TypeScript rules

**Pipeline Behavior:** The pipeline fails if any linting errors are found, ensuring code quality standards.

### 2. Unit Testing ✓
**Python Backend:**
- **pytest**: Unit testing framework
- **Coverage.py**: Code coverage reporting (minimum 70% threshold)
- Tests cover:
  - FastAPI endpoint validation
  - Celery task execution
  - Database integration (mocked Supabase)
  - Data validation using Pydantic models

**Test Results Display:**
- Test summary shown in CI logs
- Coverage report generated and displayed
- Failed tests halt the pipeline

### 3. Build Automation ✓
**Backend Build:**
- Python package installation using `pip`
- Dependency verification from `requirements.txt`
- Virtual environment setup

**Frontend Build:**
- Node.js dependency installation using `npm`
- TypeScript compilation check
- Astro build process validation

**Build Order:**
1. Linting must pass
2. Tests must pass with adequate coverage
3. Only then does the build process execute

## Pipeline Trigger Methods

### Automatic Triggers
1. **Push to main branch**
   ```bash
   git push origin main
   ```

2. **Pull Request to main**
   ```bash
   git checkout -b feature/APIinputBackend-DK
   git push origin feature/APIinputBackend-DK
   # Create PR on GitHub
   ```

3. **Manual Trigger** (via GitHub UI)
   - Navigate to "Actions" tab
   - Select the workflow
   - Click "Run workflow"


## Pipeline Workflow Steps

```
┌─────────────────────────────────────────────────────────────────┐
│  Trigger: Push to main / Pull Request / Manual                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Checkout Code                                          │
│  - Clone repository                                             │
│  - Fetch all branches                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Setup Environment                                      │
│  - Install Python 3.11                                          │
│  - Install Node.js 20                                           │
│  - Cache dependencies                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Linting (MUST PASS)                                    │
│  ├─ Backend: Flake8 + Black                                     │
│  └─ Frontend: ESLint + Prettier                                 │
│                                                                  │
│  ❌ FAIL → Pipeline stops                                       │
│  ✅ PASS → Continue                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Unit Testing (MUST PASS)                               │
│  ├─ Run pytest with coverage                                    │
│  ├─ Generate coverage report                                    │
│  └─ Verify 70% minimum coverage                                 │
│                                                                  │
│  ❌ FAIL → Pipeline stops                                       │
│  ✅ PASS → Continue                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Build Validation                                       │
│  ├─ Backend: Verify Python package integrity                    │
│  └─ Frontend: Build Astro application                           │
│                                                                  │
│  ❌ FAIL → Pipeline stops                                       │
│  ✅ PASS → Success! 🎉                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Challenges Faced

### 1. **Dependency Management Across Environments**
**Challenge:** Different Python/Node versions between local development and CI caused inconsistent behavior.

**Solution:** 
- Pinned specific versions in workflow (Python 3.11, Node 20)
- Used dependency caching to speed up builds
- Created separate `requirements-dev.txt` for testing dependencies

### 2. **Supabase Authentication in CI**
**Challenge:** Unit tests required Supabase credentials, which shouldn't be hardcoded.

**Solution:**
- Used GitHub Secrets for sensitive credentials
- Implemented mock Supabase client for unit tests
- Used environment variable fallbacks with test defaults

### 3. **Celery/Redis Dependencies in Testing**
**Challenge:** Running Celery workers requires Redis, which isn't available in GitHub Actions by default.

**Solution:**
- Mocked Celery tasks in unit tests using `unittest.mock`
- Set up Redis service container in workflow
- Used `pytest-celery` fixtures for integration tests

### 4. **Frontend Build Path Issues**
**Challenge:** Astro build process expected specific directory structure that differed in CI.

**Solution:**
- Normalized paths using environment variables
- Added pre-build validation step
- Used `npm ci` instead of `npm install` for cleaner installs

### 5. **Test Coverage Threshold Enforcement**
**Challenge:** Initially had low test coverage, pipeline kept failing.

**Solution:**
- Incrementally added unit tests for critical paths
- Set realistic initial threshold (70%)
- Added coverage report to PR comments for visibility
- Excluded non-critical files from coverage (e.g., `__init__.py`)

## Local Development vs CI

### Running Linting Locally
```bash
# Python
pip install flake8 black
flake8 . --max-line-length=88
black --check .

# TypeScript
npm install
npm run lint
```

### Running Tests Locally
```bash
# Python
pip install pytest pytest-cov
pytest --cov=. --cov-report=term-missing

# You should see coverage report similar to CI
```

### Simulating the Full Pipeline Locally
```bash
# Install pre-commit hooks to run checks on every commit
pip install pre-commit
pre-commit install

# Now linting runs automatically before each commit
git commit -m "Your message"
```

## Viewing Pipeline Results

### Via GitHub UI
1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select the latest workflow run
4. View detailed logs for each step

### Via Status Checks on PRs
- Green checkmark ✅: All checks passed
- Red X ❌: Pipeline failed (click for details)
- Yellow circle 🟡: Pipeline running

### Sample Success Output
```
✅ Linting (Python) - Passed
✅ Linting (TypeScript) - Passed
✅ Unit Tests - Passed (75% coverage)
✅ Build - Passed
```

## Configuration Files

### `.github/workflows/ci-pipeline.yml`
Main workflow configuration defining all pipeline steps.

### `pytest.ini`
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=. --cov-report=term-missing --cov-fail-under=70
```

### `.flake8`
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,node_modules
```

### `.eslintrc.json`
```json
{
  "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"]
}
```
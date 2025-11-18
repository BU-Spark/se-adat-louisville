# ADAT CI Pipeline - Q2 Demo

This is a simplified CI/CD pipeline demonstration for the Anti-Displacement Assessment Tool (ADAT) project.

## Overview

This pipeline implements automated quality checks for the ADAT data preparation module, including:
- **Code Linting**: Ensures code follows Python style guidelines
- **Unit Testing**: Validates core functions work correctly
- **Build Automation**: Confirms the module can be imported and used

## CI Tool Used

**GitHub Actions** - A cloud-based CI/CD platform integrated with GitHub repositories.

### Why GitHub Actions?
- Free for public repositories
- Easy to set up with YAML configuration
- Integrated with GitHub workflow
- No additional infrastructure needed

## Tasks Implemented

### 1. Code Linting ✅
- **Tool**: Flake8 + Black
- **Purpose**: Enforces Python PEP 8 style guidelines and consistent formatting
- **What it checks**:
  - Line length (max 100 characters)
  - Proper indentation
  - Import ordering
  - Unused variables
  - Code complexity

### 2. Unit Testing ✅
- **Tool**: pytest with coverage reporting
- **Purpose**: Validates that core functions work correctly
- **Test Coverage**:
  - `med_lin_est()` - Median linear interpolation
  - `renter_adj()` - FMI adjustment calculation
  - `calculate_risk_level()` - Displacement risk assessment
  - `validate_project_data()` - Input validation
- **Metrics**: Provides code coverage percentage

### 3. Build Automation ✅
- **Purpose**: Ensures the Python module is importable and dependencies are correct
- **Steps**:
  - Installs all dependencies from requirements.txt
  - Validates Python syntax
  - Tests module imports
  - Confirms no runtime errors

## Project Structure

```
ADAT-CI-Demo/
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions pipeline config
│
├── data_prep_simple.py            # Simplified ADAT data prep module
├── test_data_prep.py              # Unit tests
├── requirements.txt                # Python dependencies
└── README.md                      # This file
```

## How to Set Up and Trigger the Pipeline

### Step 1: Create Repository Structure

1. Create a new GitHub repository (or use existing ADAT repo)
2. Create the folder structure:
   ```bash
   mkdir -p .github/workflows
   ```

### Step 2: Add Files

Copy these files to your repository:
- `data_prep_simple.py` → root directory
- `test_data_prep.py` → root directory
- `requirements.txt` → root directory
- `.github-workflows-ci.yml` → rename and move to `.github/workflows/ci.yml`

### Step 3: Commit and Push

```bash
git add .
git commit -m "Add CI pipeline for ADAT"
git push origin main
```

### Step 4: Pipeline Triggers Automatically!

The pipeline runs automatically on:
- **Push to main/master/dev branches**
- **Pull requests to main/master/dev**
- **Manual trigger** (via GitHub Actions tab)

### Viewing Results

1. Go to your GitHub repository
2. Click the "Actions" tab
3. See the pipeline status (✓ passed or ✗ failed)
4. Click on any run to see detailed logs

## Running Tests Locally

You can run all checks locally before pushing:

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Linting
```bash
# Flake8
flake8 data_prep_simple.py --max-line-length=100

# Black (auto-format)
black data_prep_simple.py --line-length=100
```

### Run Tests
```bash
# Run all tests with coverage
pytest test_data_prep.py -v --cov=data_prep_simple --cov-report=term-missing

# Run specific test class
pytest test_data_prep.py::TestCalculateRiskLevel -v
```

### Validate Module
```bash
# Check syntax
python -c "import py_compile; py_compile.compile('data_prep_simple.py', doraise=True)"

# Test imports
python -c "from data_prep_simple import calculate_risk_level; print('Success!')"
```

## Test Results Summary

When you run the pipeline, you should see:

```
✓ Linting: PASSED
  - Flake8: 0 errors
  - Black: Formatted correctly

✓ Testing: PASSED  
  - 12 tests passed
  - Code coverage: 95%

✓ Build: PASSED
  - All dependencies installed
  - Module imports successfully
```

## Challenges Faced

### 1. **Dependency Management**
- **Issue**: The full ADAT data_prep.py has many heavy dependencies (geopandas, shapely, etc.)
- **Solution**: Created simplified version focusing on core logic functions
- **Benefit**: Faster CI runs, easier to test

### 2. **Test Data Requirements**
- **Issue**: Original R code processes large census datasets
- **Solution**: Created unit tests with mock data that test logic without requiring actual data files
- **Benefit**: Tests run quickly and don't need data downloads

### 3. **Python/R Translation**
- **Issue**: Original tool is in R, needs Python equivalent
- **Solution**: Focused on translating core calculation functions that are language-agnostic
- **Benefit**: Demonstrates migration path from R to Python

### 4. **CI Configuration**
- **Issue**: GitHub Actions syntax and proper step ordering
- **Solution**: Used clear step names and continue-on-error: false to fail fast
- **Benefit**: Clear feedback on what failed and where

## Future Enhancements

For a production pipeline, consider adding:
- **Integration Tests**: Test full data processing pipeline
- **Security Scanning**: Check for vulnerabilities in dependencies
- **Docker Build**: Containerize the application
- **Deployment**: Auto-deploy to staging/production
- **Performance Tests**: Ensure processing speed meets requirements
- **Documentation Generation**: Auto-generate API docs

## Quick Start Guide

**To complete the Q2 Demo assignment:**

1. Copy all provided files to your repository
2. Push to GitHub
3. Go to Actions tab and watch the pipeline run
4. Take screenshots of:
   - Pipeline success screen
   - Test results
   - Coverage report
5. Submit this README with your screenshots

## Contact

For questions about this CI setup:
- See project documentation in `/docs`
- Contact ADAT team at Initiative on Cities, BU

---

**Pipeline Status**: ✅ Ready for Demo  
**Last Updated**: November 2025  
**Python Version**: 3.11+

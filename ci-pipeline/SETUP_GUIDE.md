# ADAT Q2 Demo - Complete Setup Guide

## 📋 What You're Submitting

A working CI pipeline that automatically:
1. **Lints** your Python code (Flake8 + Black)
2. **Tests** your code (pytest with 12 unit tests)
3. **Builds** your module (validates imports)

## 🚀 Quick Start (5 Minutes)

### Option A: If you already have a GitHub repo

1. **Copy files to your repo:**
   ```bash
   # Copy these files from the provided package:
   data_prep_simple.py
   test_data_prep.py
   requirements.txt
   README.md
   ```

2. **Create GitHub Actions folder:**
   ```bash
   mkdir -p .github/workflows
   ```

3. **Move CI config:**
   ```bash
   # Rename and move the CI file:
   mv .github-workflows-ci.yml .github/workflows/ci.yml
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add CI pipeline for ADAT Q2 demo"
   git push origin main
   ```

5. **View results:**
   - Go to your repo on GitHub
   - Click "Actions" tab
   - Watch the pipeline run!

### Option B: Starting from scratch

1. **Create new repo on GitHub:**
   - Go to github.com
   - Click "New repository"
   - Name it: `adat-ci-demo`
   - Make it public
   - Click "Create repository"

2. **Clone and setup locally:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/adat-ci-demo.git
   cd adat-ci-demo
   
   # Copy all provided files into this directory
   # Then run:
   bash setup.sh
   ```

3. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Initial commit with CI pipeline"
   git push origin main
   ```

## 🧪 Test Locally First (Recommended)

Before pushing to GitHub, test everything works:

```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
flake8 data_prep_simple.py --max-line-length=100
black --check data_prep_simple.py --line-length=100

# Run tests
pytest test_data_prep.py -v --cov=data_prep_simple

# Validate module
python -c "from data_prep_simple import calculate_risk_level; print('✓ Import successful')"
```

If all these pass locally, they'll pass in CI!

## 📊 What the CI Pipeline Does

### Step 1: Code Linting
```
Checks:
✓ Line length < 100 characters
✓ Proper indentation (4 spaces)
✓ No unused imports
✓ PEP 8 compliance

Tools: Flake8 + Black
```

### Step 2: Unit Testing
```
Runs 12 tests:
✓ med_lin_est (3 tests) - Median calculation
✓ renter_adj (2 tests) - FMI adjustment
✓ calculate_risk_level (3 tests) - Risk assessment
✓ validate_project_data (4 tests) - Input validation

Tool: pytest with coverage
Expected: 12 passed, ~95% coverage
```

### Step 3: Build Validation
```
Checks:
✓ Install all dependencies
✓ Python syntax is valid
✓ Module can be imported
✓ No runtime errors

Tool: Python compiler + import test
```

## 📸 What to Screenshot for Submission

1. **Actions Tab Overview**
   - Shows green checkmark ✓
   - Shows "CI Pipeline" workflow

2. **Pipeline Run Details**
   - All three jobs passed
   - Shows execution time

3. **Test Results**
   - "12 tests passed"
   - Coverage report

4. **README.md**
   - Your completed README

## 🐛 Troubleshooting

### Pipeline Fails on Linting
**Problem:** Flake8 or Black errors

**Solution:**
```bash
# Auto-fix formatting
black data_prep_simple.py --line-length=100

# Check what's wrong
flake8 data_prep_simple.py --max-line-length=100
```

### Pipeline Fails on Tests
**Problem:** Tests don't pass

**Solution:**
```bash
# Run tests locally to see error
pytest test_data_prep.py -v

# Run specific failing test
pytest test_data_prep.py::TestName::test_name -v
```

### Pipeline Fails on Build
**Problem:** Import or dependency errors

**Solution:**
```bash
# Check syntax
python -m py_compile data_prep_simple.py

# Test import
python -c "import data_prep_simple"

# Check dependencies
pip install -r requirements.txt
```

### "Workflow file not found"
**Problem:** CI file in wrong location

**Solution:**
```bash
# Must be exactly here:
.github/workflows/ci.yml

# NOT here:
.github-workflows-ci.yml  ❌
```

## ✅ Success Criteria

Your pipeline passes when you see:

```
✓ Linting: PASSED
  - Flake8: 0 errors
  - Black: Formatting correct

✓ Testing: PASSED
  - 12/12 tests passed
  - Coverage: ~95%

✓ Build: PASSED
  - Dependencies installed
  - Module imports successfully
```

## 📝 Assignment Deliverables Checklist

- [ ] All files in repository
- [ ] CI pipeline runs automatically on push
- [ ] All tests pass (green checkmark)
- [ ] README.md explains the setup
- [ ] Screenshots of successful run
- [ ] Short write-up of challenges (see README)

## 🎯 Grading Rubric Alignment

| Requirement | Implementation | Points |
|------------|----------------|--------|
| Code Linting | Flake8 + Black | ✓ |
| Unit Testing | pytest (12 tests) | ✓ |
| Build Automation | Import validation | ✓ |
| README Documentation | Comprehensive guide | ✓ |
| Pipeline Triggers | Push/PR/Manual | ✓ |

## 💡 Tips for Demo Day

1. **Before presenting:**
   - Make sure pipeline is green ✓
   - Have GitHub Actions tab open
   - Know your test coverage %

2. **What to highlight:**
   - "Runs automatically on every push"
   - "12 tests, 95% coverage"
   - "Catches errors before code review"

3. **If asked about challenges:**
   - See "Challenges Faced" in README.md
   - Mention simplified vs. full implementation
   - Discuss Python/R translation

## 🔗 Useful Links

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **pytest Documentation:** https://docs.pytest.org
- **Flake8 Guide:** https://flake8.pycqa.org
- **Your ADAT Project:** [Link to project doc]

## 📞 Getting Help

If stuck:
1. Check troubleshooting section above
2. Run tests locally first
3. Check GitHub Actions logs for errors
4. Ask instructor or TA

---

**Time Estimate:** 15-30 minutes total setup
**Difficulty:** Easy - all code provided
**Grade Impact:** 10 points (Q2 Demo)

Good luck! 🚀

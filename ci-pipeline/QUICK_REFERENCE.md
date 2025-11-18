# 📋 ADAT CI Pipeline - Quick Reference Card

## 🚀 Setup Commands (Copy & Paste)

```bash
# Step 1: Create workflows folder
mkdir -p .github/workflows

# Step 2: Move CI file
mv ci.yml .github/workflows/ci.yml

# Step 3: Commit and push
git add .
git commit -m "Add CI pipeline"
git push origin main
```

## 📁 Required File Locations

```
your-repo/
├── .github/
│   └── workflows/
│       └── ci.yml          ← Must be here!
├── data_prep_simple.py     ← Root directory
├── test_data_prep.py       ← Root directory
├── requirements.txt         ← Root directory
└── README.md               ← Root directory
```

## ✅ Pre-Push Checklist

```bash
# Test locally before pushing:
pip install -r requirements.txt
pytest test_data_prep.py -v
flake8 data_prep_simple.py --max-line-length=100
```

## 🎯 Expected Results

```
✓ Linting: PASSED (0 errors)
✓ Testing: PASSED (12/12 tests)
✓ Build: PASSED (imports work)
Total time: ~1-2 minutes
```

## 🐛 Common Fixes

| Problem | Solution |
|---------|----------|
| Workflow not found | Move ci.yml to .github/workflows/ |
| Linting fails | Run `black data_prep_simple.py` |
| Tests fail | Run `pytest test_data_prep.py -v` locally |
| Import errors | Check requirements.txt is present |

## 📸 What to Screenshot

1. Green checkmark in Actions tab
2. Pipeline run details (all steps passed)
3. Test results (12 passed)
4. README.md on GitHub

## 💯 Grading Rubric

- 2pts: Code Linting ✅
- 3pts: Unit Testing ✅
- 2pts: Build Automation ✅  
- 2pts: README Documentation ✅
- 1pt: Challenges Section ✅

**Total: 10 points** 🎯

## 🔗 File Purpose

| File | What It Does |
|------|--------------|
| ci.yml | Defines CI pipeline |
| data_prep_simple.py | Code being tested |
| test_data_prep.py | 12 unit tests |
| requirements.txt | Dependencies |
| README.md | Documentation |

## ⏱️ Time Estimates

- Setup: 5-10 minutes
- First push: 1-2 minutes (pipeline runs)
- Troubleshooting: 5-15 minutes (if needed)
- **Total: 10-25 minutes max**

## 🎓 Key Concepts

**CI/CD:** Continuous Integration / Continuous Deployment
**Linting:** Automatic code style checking
**Unit Tests:** Small tests for individual functions
**Build:** Compile and validate code can run

## 🆘 Emergency Help

1. Read START_HERE.md first
2. Check SETUP_GUIDE.md for detailed steps
3. Look at VISUAL_GUIDE.md for diagrams
4. Test locally before pushing
5. Check GitHub Actions logs for errors

---

**Save this card for quick reference during setup!** 📌

**Questions? See the full guides:**
- START_HERE.md - Overview
- SETUP_GUIDE.md - Step-by-step
- VISUAL_GUIDE.md - Diagrams
- README.md - Full documentation

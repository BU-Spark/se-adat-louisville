# ADAT CI Pipeline - Visual Workflow

## 🔄 Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  TRIGGER: Push to GitHub or Pull Request                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: CHECKOUT CODE                                       │
│  ─────────────────────────────────────────────────────────  │
│  • Clone repository                                          │
│  • Set up Python 3.11                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: CODE LINTING ✓                                      │
│  ─────────────────────────────────────────────────────────  │
│  Tool: Flake8 + Black                                        │
│  ─────────────────────────────────────────────────────────  │
│  Checks:                                                     │
│  ✓ Line length (max 100)                                     │
│  ✓ PEP 8 style guide                                         │
│  ✓ Code formatting                                           │
│  ✓ No unused imports                                         │
│                                                              │
│  If FAIL → Pipeline stops ❌                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: UNIT TESTING ✓                                      │
│  ─────────────────────────────────────────────────────────  │
│  Tool: pytest                                                │
│  ─────────────────────────────────────────────────────────  │
│  Tests:                                                      │
│  ✓ med_lin_est() - 3 tests                                   │
│  ✓ renter_adj() - 2 tests                                    │
│  ✓ calculate_risk_level() - 3 tests                          │
│  ✓ validate_project_data() - 4 tests                         │
│                                                              │
│  Total: 12 tests                                             │
│  Coverage: ~95%                                              │
│                                                              │
│  If FAIL → Pipeline stops ❌                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: BUILD AUTOMATION ✓                                  │
│  ─────────────────────────────────────────────────────────  │
│  Actions:                                                    │
│  ✓ Install dependencies (requirements.txt)                   │
│  ✓ Compile Python bytecode                                   │
│  ✓ Verify module imports                                     │
│  ✓ Check no runtime errors                                   │
│                                                              │
│  If FAIL → Pipeline stops ❌                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ✓ SUCCESS! All Checks Passed                                │
│  ─────────────────────────────────────────────────────────  │
│  Result: Green checkmark on GitHub ✅                        │
│  Notification: Email/GitHub notification sent                │
│  Status: Ready to merge/deploy                               │
└─────────────────────────────────────────────────────────────┘
```

## 📊 File Structure After Setup

```
your-adat-repo/
│
├── .github/
│   └── workflows/
│       └── ci.yml              ← GitHub Actions config
│
├── data_prep_simple.py         ← Main module (simplified ADAT)
├── test_data_prep.py           ← Unit tests (12 tests)
├── requirements.txt             ← Python dependencies
├── README.md                   ← Project documentation
├── SETUP_GUIDE.md              ← This guide
└── setup.sh                    ← Quick setup script
```

## 🎯 Test Coverage Map

```
data_prep_simple.py Functions:
├── med_lin_est()                    [TESTED ✓] - 3 tests
│   ├── Basic median calculation
│   ├── Empty values handling  
│   └── Single bin edge case
│
├── renter_adj()                     [TESTED ✓] - 2 tests
│   ├── Basic FMI adjustment
│   └── High FMI edge case
│
├── calculate_risk_level()           [TESTED ✓] - 3 tests
│   ├── High risk scenario
│   ├── Medium risk scenario
│   └── Low risk scenario
│
└── validate_project_data()          [TESTED ✓] - 4 tests
    ├── Valid project data
    ├── Missing fields
    ├── Invalid units
    └── Affordability constraints

Total Coverage: ~95%
```

## 🚦 Decision Tree: When Pipeline Runs

```
Event Occurs
     │
     ├─► Push to main/master/dev? ──────► YES ──► Run Pipeline
     │
     ├─► Pull Request opened? ───────────► YES ──► Run Pipeline
     │
     ├─► Manual trigger? ─────────────────► YES ──► Run Pipeline
     │
     └─► Push to other branch? ───────────► NO ───► Skip
```

## 📈 Expected Results Timeline

```
Time    Action
────────────────────────────────────────────────────────
0:00    Push code to GitHub
0:05    GitHub Actions triggered
0:10    Environment setup complete
0:30    Linting complete ✓
0:45    Testing complete ✓ (12/12 passed)
1:00    Build complete ✓
1:05    Pipeline finished - Green checkmark ✅
```

## 🔍 What Each Step Validates

### Linting Phase
```
Input:  data_prep_simple.py
         ↓
Check:  Style, formatting, complexity
         ↓
Output: PASS ✓ or detailed error list ❌
```

### Testing Phase  
```
Input:  data_prep_simple.py + test_data_prep.py
         ↓
Run:    12 unit tests with coverage
         ↓
Output: X/12 passed, coverage % ✓
```

### Build Phase
```
Input:  All project files + requirements.txt
         ↓
Check:  Dependencies, imports, compilation
         ↓
Output: Module ready for use ✓
```

## 💰 Value Proposition

**Before CI:**
- Manual testing required
- Style inconsistencies
- Bugs found late
- Time: ~30 min per check

**After CI:**
- Automatic testing
- Consistent style
- Bugs found immediately  
- Time: ~1 minute

**ROI:** Saves ~29 minutes per commit × N commits

## 🎓 Learning Outcomes

By completing this demo, you've learned:

✓ How to set up GitHub Actions
✓ Writing unit tests with pytest
✓ Code linting and formatting
✓ Build automation basics
✓ CI/CD pipeline concepts
✓ Test-driven development
✓ DevOps best practices

---

**Remember:** The goal isn't perfection, it's demonstrating understanding of CI/CD concepts! 🎯

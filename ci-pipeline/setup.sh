#!/bin/bash
# ADAT CI Pipeline - Quick Setup Script

echo "=========================================="
echo "ADAT CI Pipeline Setup"
echo "=========================================="
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "⚠️  Not a git repository. Initializing..."
    git init
    echo "✓ Git repository initialized"
fi

# Create .github/workflows directory
echo "Creating directory structure..."
mkdir -p .github/workflows

# Move CI configuration
if [ -f ".github-workflows-ci.yml" ]; then
    mv .github-workflows-ci.yml .github/workflows/ci.yml
    echo "✓ CI configuration moved to .github/workflows/ci.yml"
else
    echo "⚠️  .github-workflows-ci.yml not found"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review files:"
echo "   - data_prep_simple.py (main module)"
echo "   - test_data_prep.py (unit tests)"
echo "   - .github/workflows/ci.yml (CI pipeline)"
echo ""
echo "2. Test locally:"
echo "   pip install -r requirements.txt"
echo "   pytest test_data_prep.py -v"
echo ""
echo "3. Push to GitHub:"
echo "   git add ."
echo "   git commit -m 'Add CI pipeline'"
echo "   git push origin main"
echo ""
echo "4. Check pipeline:"
echo "   Go to GitHub → Actions tab"
echo ""

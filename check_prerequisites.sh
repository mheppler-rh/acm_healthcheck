#!/bin/bash
#
# Prerequisites checker for ACM Health Check tool
#

echo "Checking prerequisites for ACM Health Check..."
echo "=============================================="
echo

all_ok=true

# Check Python 3
echo -n "Python 3: "
if command -v python3 &> /dev/null; then
    version=$(python3 --version 2>&1)
    echo "✓ $version"
else
    echo "✗ NOT FOUND"
    echo "  Install: sudo dnf install python3  (RHEL/Fedora)"
    echo "           sudo apt install python3  (Debian/Ubuntu)"
    all_ok=false
fi

# Check OMC
echo -n "OMC CLI: "
if command -v omc &> /dev/null; then
    version=$(omc version 2>&1 | head -1 || echo "installed")
    echo "✓ $version"
else
    echo "✗ NOT FOUND"
    echo "  Install from: https://github.com/gmeghnag/omc/releases"
    all_ok=false
fi

# Check PyYAML
echo -n "PyYAML: "
if python3 -c "import yaml" 2>/dev/null; then
    echo "✓ installed"
else
    echo "✗ NOT INSTALLED"
    echo "  Install: pip install PyYAML"
    all_ok=false
fi

# Check omc-python
echo -n "omc-python library: "
if [ -d "omc-python/omc" ]; then
    echo "✓ found"
else
    echo "✗ NOT FOUND"
    echo "  Error: omc-python directory missing"
    all_ok=false
fi

# Check script
echo -n "acm_healthcheck.py: "
if [ -f "acm_healthcheck.py" ]; then
    if [ -x "acm_healthcheck.py" ]; then
        echo "✓ found and executable"
    else
        echo "⚠ found but not executable"
        echo "  Run: chmod +x acm_healthcheck.py"
    fi
else
    echo "✗ NOT FOUND"
    all_ok=false
fi

echo
echo "=============================================="

if [ "$all_ok" = true ]; then
    echo "✓ All prerequisites met!"
    echo
    echo "Ready to run:"
    echo "  ./acm_healthcheck.py /path/to/must-gather"
    exit 0
else
    echo "✗ Some prerequisites missing"
    echo
    echo "Please install missing components and try again."
    exit 1
fi

# Installation Guide

## Prerequisites

### 1. Python 3.8 or later

Check your Python version:
```bash
python3 --version
```

If you need to install Python:
- **RHEL/CentOS/Fedora**: `sudo dnf install python3`
- **Ubuntu/Debian**: `sudo apt install python3`
- **macOS**: `brew install python3`

### 2. OMC CLI Tool

The OMC (Offline Must-Gather CLI) tool is required.

**Install from GitHub releases:**

```bash
# Download latest release
# Visit: https://github.com/gmeghnag/omc/releases

# Example for Linux (adjust version as needed)
wget https://github.com/gmeghnag/omc/releases/download/vX.X.X/omc_Linux_x86_64.tar.gz
tar -xzf omc_Linux_x86_64.tar.gz
sudo mv omc /usr/local/bin/
chmod +x /usr/local/bin/omc

# Verify installation
omc version
```

**Or build from source:**

```bash
git clone https://github.com/gmeghnag/omc.git
cd omc
go build -o omc
sudo mv omc /usr/local/bin/
```

## Installation Steps

### 1. Clone or Download

If you have this in a git repository:
```bash
git clone <repository-url>
cd acm_healthcheck
```

Or if you have the files:
```bash
cd acm_healthcheck
```

### 2. Install Python Dependencies

```bash
cd omc-python
pip install -r requirements.txt
pip install -e .
```

Or system-wide:
```bash
cd acm_healthcheck
sudo pip3 install -r omc-python/requirements.txt
```

### 3. Make Executable

```bash
chmod +x acm_healthcheck.py
```

### 4. Test Installation

```bash
# Check help works
./acm_healthcheck.py --help

# Check version
./acm_healthcheck.py --version
```

## Verification

Run this verification script:

```bash
#!/bin/bash
echo "Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    echo "✓ Python 3 installed: $(python3 --version)"
else
    echo "✗ Python 3 not found"
    exit 1
fi

# Check OMC
if command -v omc &> /dev/null; then
    echo "✓ OMC installed: $(omc version 2>&1 | head -1)"
else
    echo "✗ OMC not found"
    exit 1
fi

# Check PyYAML
if python3 -c "import yaml" 2>/dev/null; then
    echo "✓ PyYAML installed"
else
    echo "✗ PyYAML not installed"
    echo "  Run: pip install PyYAML"
    exit 1
fi

echo ""
echo "✓ All prerequisites met!"
echo "Ready to run: ./acm_healthcheck.py /path/to/must-gather"
```

Save as `check_prerequisites.sh`, make executable, and run:
```bash
chmod +x check_prerequisites.sh
./check_prerequisites.sh
```

## Usage

Once installed:

```bash
# Run health check on a must-gather
./acm_healthcheck.py /path/to/must-gather

# Example
./acm_healthcheck.py ~/support-cases/12345/must-gather.local.12345
```

## Troubleshooting

### "OMC not found"

```
Error: OMC not found at 'omc'. Install from https://github.com/gmeghnag/omc
```

**Solution**: 
- Ensure OMC is installed and in your PATH
- Try: `which omc` to verify
- If installed elsewhere, you can specify the path (future feature)

### "ModuleNotFoundError: No module named 'omc'"

```
ModuleNotFoundError: No module named 'omc'
```

**Solution**:
```bash
cd omc-python
pip install -e .
```

### "Not a valid must-gather"

```
Not a valid must-gather - namespaces directory not found
```

**Solution**:
- Ensure you're pointing to the **extracted** must-gather directory
- Not the tarball (.tar.gz) - extract it first
- The directory should contain a `namespaces/` subdirectory

### Permission Denied

```
-bash: ./acm_healthcheck.py: Permission denied
```

**Solution**:
```bash
chmod +x acm_healthcheck.py
```

## Uninstallation

To remove:

```bash
# Remove the directory
cd ..
rm -rf acm_healthcheck

# Optionally remove OMC
sudo rm /usr/local/bin/omc
```

## Support

This tool is provided as-is without warranty. For issues:
- Check the troubleshooting section above
- Verify prerequisites are met
- Ensure must-gather is valid and extracted

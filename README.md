# RHACM Health Check Tool (Python Version)

Python conversion of the [Red Hat Advanced Cluster Management (RHACM)](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/) must-gather analysis bash script using the omc-python library.

## Overview

This tool analyzes Red Hat Advanced Cluster Management (RHACM) must-gather archives and provides:
- Cluster health information
- Component status (RHACM, MCE, OCP)
- Pod health and error detection
- Configuration validation

## Quick Start

```bash
# Make executable
chmod +x acm_healthcheck.py

# Run health check
./acm_healthcheck.py /path/to/must-gather
```

## Prerequisites

1. **Python 3.8+**
2. **OMC CLI tool** installed and in PATH
   - Install from: https://github.com/gmeghnag/omc
3. **Python Dependencies**: PyYAML, colorama, python-dateutil

## Installation

```bash
cd acm_healthcheck

# Install Python dependencies
pip install -r omc-python/requirements.txt

# Make executable
chmod +x acm_healthcheck.py

# Run
./acm_healthcheck.py /path/to/must-gather
```

## Usage

### Basic Command

```bash
./acm_healthcheck.py /path/to/must-gather
```

### Force Must-Gather Type

Override auto-detection and force the must-gather type:

```bash
# Force RHACM must-gather analysis
./acm_healthcheck.py -t ACM /path/to/must-gather

# Force OCP must-gather analysis
./acm_healthcheck.py -t OCP /path/to/must-gather
```

This is useful when auto-detection fails or when you want to analyze an OCP must-gather with RHACM-specific checks disabled.

### Verbose Mode

Show detailed information about managed clusters (name, state, OCP version, compatibility):

```bash
./acm_healthcheck.py -v /path/to/must-gather
# or
./acm_healthcheck.py --verbose /path/to/must-gather
```

In verbose mode, the tool will:
- Display each managed cluster's name, availability state, and OCP version
- Check OCP version compatibility against the installed RHACM version
- Warn about unsupported OCP versions with specific compatibility details

### Debug Mode

Show detailed diagnostic information for troubleshooting:

```bash
./acm_healthcheck.py -d /path/to/must-gather
# or
./acm_healthcheck.py --debug /path/to/must-gather
```

In debug mode, the tool will:
- Show internal processing steps
- Display subscription lookups and version detection
- Show compatibility checking logic
- Help diagnose issues with must-gather analysis

You can combine verbose and debug modes:

```bash
./acm_healthcheck.py -v -d /path/to/must-gather
```

### Help

```bash
./acm_healthcheck.py --help
```

### Version

```bash
./acm_healthcheck.py --version
```

## What Gets Checked

### For RHACM Hub Clusters

- ✅ Must-gather type detection (RHACM/OCP)
- ✅ RHACM/MCE version information
- ✅ Environment type (Connected/Disconnected)
- ✅ MCH (MultiClusterHub) health
  - Current vs Desired version
  - Phase status
  - Backup configuration
- ✅ MCE (MultiCluster Engine) health
  - Current vs Desired version
  - Phase status
  - Component status (verbose mode)
- ✅ Hub cluster details
  - Cluster name, ID, version
  - Platform (AWS, Azure, etc.)
  - Node counts
- ✅ Managed clusters count
- ✅ RHACM namespace validation
- ✅ Pod counts per RHACM namespace
- ✅ Addon pod status
- ✅ Klusterlet pod status
- ✅ Pods in error state
- ✅ Pods with high restart counts (>10)

### For RHACM Managed Clusters

- ✅ Environment type
- ✅ Addon status
- ✅ Klusterlet status
- ✅ Pod error checking

### For OCP Clusters

- ✅ Cluster platform
- ✅ Environment type
- ✅ ETCD status
- ✅ Node status
- ✅ Pod error checking

## Example Output

```
Collecting environment details using must-gather:
must-gather.local.1234567890

Must-Gather Image: RHACM
Hub Cluster: Yes
RHACM Version: 2.7.0
MCE Version: 2.2.0

Environment Type: Connected

MCH Health:
    Current Version: 2.7.0
    Desired Version: 2.7.0
    Phase: Running
    Backup Enabled: false

MCE Health:
    Current Version: 2.2.0
    Desired Version: 2.2.0
    Phase: Available

Hub Cluster Details:
    Cluster Name: cluster1
    ClusterID: 12345678-1234-1234-1234-123456789012
    OpenShift Version: 4.12.0
    Desired Version: 4.12.0
    Cluster Platform: AWS
    Control Plane Nodes: 3
    Compute Nodes: 3

...
```

## Improvements Over Bash Version

### ✅ Better CLI Interface
- **Before**: Interactive select prompts
- **Now**: Direct command-line argument
- More automation-friendly

### ✅ Modern Python
- Object-oriented design
- Type hints
- Better error handling
- Uses omc-python library

### ✅ Maintainability
- Modular check functions
- Reusable code patterns
- Easier to extend
- Clear separation of concerns

### ✅ Integration
- Can be imported as a module
- Better for automation
- Exit codes for scripting

## Project Structure

```
acm_healthcheck/
├── acm_healthcheck.py           # Main Python tool
├── acm_healthcheck_original.sh  # Original bash script (reference)
├── omc-python/                  # OMC Python library
│   ├── omc/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── commands.py
│   │   ├── resources.py
│   │   └── utils.py
│   ├── examples/
│   ├── requirements.txt
│   └── README.md
└── README.md                     # This file
```

## Troubleshooting

### OMC not found

```
Error: OMC not found at 'omc'
```

**Solution**: Install OMC CLI tool
```bash
# Download from https://github.com/gmeghnag/omc
# Or install from releases
```

### Invalid must-gather

```
Not a valid must-gather - namespaces directory not found
```

**Solution**: Ensure you're pointing to the extracted must-gather directory, not the tarball.

### Module not found

```
ModuleNotFoundError: No module named 'omc'
```

**Solution**: Install dependencies
```bash
cd omc-python
pip install -r requirements.txt
pip install -e .
```

## Adding Custom Checks

To add a new check function:

```python
def check_my_feature(self):
    """Check my custom feature."""
    self.print_header("My Feature Status:")

    # Use self.client to run OMC commands
    pods = self.client.get_pods(namespace="my-namespace")

    # Your analysis logic here
    for pod in pods:
        print(f"    {pod.name}: {pod.phase}")

    print()
```

Then add it to the `run_checks()` method.

## Future Enhancements

Potential additions:

- [ ] JSON output format (`--json`)
- [ ] HTML report generation
- [ ] Observability detailed checks
- [ ] Insights rule integration
- [ ] Alerts firing detection
- [ ] Certificate expiration checks
- [ ] Comparison mode (compare two must-gathers)
- [ ] Interactive TUI mode

## Credits

- **Original bash script**: Ryan Spagnola (rspagnol@redhat.com)
- **Python conversion**: Using omc-python library
- **Version**: 2.0

## License

All software provided is unsupported and provided as-is, without warranty of any kind.

CC0 Public Domain Dedication.

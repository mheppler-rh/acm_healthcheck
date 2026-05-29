# Changelog

## [2.1] - 2026-05-22

### Changed
- **Enhanced MCE health check**
  - Now uses OMC library (`omc get multiclusterengine`) instead of file parsing
  - Shows component status in verbose mode
  - Better error handling for missing MCE installations
- **Replaced ANSI codes with colorama** for better cross-platform color support
- Colors now work correctly on Windows and all terminal types
- Auto-reset feature prevents color bleeding
- **Pod output format changed to OMC-like table style**
  - Compact table format with columns: NAMESPACE, NAME, READY, STATUS, RESTARTS
  - Color-coded status: Green (Running/Ready), Yellow (Pending/Partial), Red (Error/Not Ready)
  - Color-coded restarts: Normal (0), Yellow (1-10), Red (>10)
  - Applies to all pod listings: addons, klusterlet, ETCD, error pods, high-restart pods
- **Refactored pod status checks** to use OMC library instead of regex parsing
  - `check_klusterlet_status()` now uses `client.get_pods()`
  - `check_addon_status()` now uses `client.get_pods()`
  - `check_etcd_status()` now uses formatted pod output
  - `check_pods_error()` now shows detailed pod information with restart counts and failure reasons
  - `check_nodes()` now shows detailed node information with not-ready reasons
- **Refactored namespace detection** to use OMC library
  - `_detect_mg_type()` now uses `client.get_pods()`
  - `_detect_hub_cluster()` now uses `client.get()`
  - `check_acm_namespaces()` now uses `client.get()` and shows which namespaces are missing
  - `check_acm_pod_counts()` now uses `client.get()` and shows running/error counts
  - `check_managed_clusters()` now uses `client.get()`
- **Version compatibility warnings** now shown even without `-v` flag
  - Displays unsupported managed cluster versions in normal mode
  - Full details still require `-v` flag

### Added
- **Verbose mode** (`-v` or `--verbose` flag)
  - Shows detailed managed cluster information: name, state (Available/Unavailable), and OCP version
  - Color-coded cluster states for easy visual scanning
  - **ACM/OCP version compatibility checking**: Validates managed cluster OCP versions against ACM support matrix
  - Displays warnings for unsupported OCP versions with compatibility details
- **Debug mode** (`-d` or `--debug` flag)
  - Shows detailed diagnostic information for troubleshooting
  - Displays internal processing steps and version detection logic
  - Can be combined with verbose mode
- **Force must-gather type** (`-t` or `--type` flag)
  - Override auto-detection with `-t ACM` or `-t OCP`
  - Useful when auto-detection fails or for testing
  - Case-insensitive (ACM/acm, OCP/ocp)
- **Enhanced resource formatting** in omc-python library
  - Added `__str__` and `__repr__` methods to all resource classes
  - Pod output shows status, restart count, and failure reasons
  - Node output shows ready/schedulable state and failure reasons
  - Event output shows type, reason, count, and involved objects
  - Deployment output shows replica status and availability reasons
  - All outputs are color-coded for easy visual scanning
- **Better namespace checking**
  - Shows which specific namespaces are missing instead of generic "not all present" message

## [2.0] - 2026-05-20

### Changed - Major Rewrite
- **Complete Python rewrite** of the original bash script
- **Object-oriented design** using `ACMHealthCheck` class
- **Uses omc-python library** instead of direct OMC CLI calls
- **Command-line arguments** instead of interactive prompts
- Better error handling and logging

### Added
- Command-line argument parsing with argparse
- `--version` flag
- `--help` documentation
- Proper exit codes for scripting
- Type hints throughout
- Comprehensive docstrings
- ANSI color codes via `Colors` class
- Modular check methods

### Features Implemented
- ✅ Must-gather validation
- ✅ ACM/OCP detection
- ✅ Hub/Managed cluster detection
- ✅ Version detection (ACM, MCE, OCP)
- ✅ Environment type detection (Connected/Disconnected)
- ✅ MCH health checks
- ✅ MCE health checks
- ✅ Hub cluster details
- ✅ Managed clusters count
- ✅ ACM namespace validation
- ✅ Pod counts per namespace
- ✅ Addon status checks
- ✅ Klusterlet status checks
- ✅ Pods in error state detection
- ✅ High restart count detection (>10)
- ✅ ETCD status (OCP mode)
- ✅ Node status (OCP mode)

### Not Yet Implemented
- ❌ Observability detailed checks (Thanos compactor, etc.)
- ❌ Insights rule checking
- ❌ Alerts firing detection
- ❌ Events detailed listing

### Technical Improvements
- Regex-based parsing instead of awk/sed
- Path handling using pathlib
- Better file searching with rglob
- Exception handling
- Consistent output formatting

## [1.0] - Original

### Features
- Original bash script by Ryan Spagnola
- Interactive case and must-gather selection
- Comprehensive ACM health checks
- Observability checks
- Insights integration
- Alert monitoring
- Event tracking

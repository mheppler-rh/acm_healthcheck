#!/usr/bin/env python3
"""
ACM Health Check Tool

Analyzes Red Hat Advanced Cluster Management must-gather archives.

Author: Converted from bash script by Ryan Spagnola
Version: 2.1 (Python)

All software provided below is unsupported and provided as-is, without
warranty of any kind.
"""

import sys
import os
import argparse
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from colorama import Fore, Style, init

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Add omc-python to path
sys.path.insert(0, str(Path(__file__).parent / "omc-python"))

from omc import OMCClient
from omc.utils import get_failing_pods


# ACM to OCP version compatibility matrix
# Based on Red Hat documentation: https://access.redhat.com/support/policy/updates/advanced-cluster-management
# ACM supports: latest RHOCP + 2 previous versions + next upcoming version
ACM_OCP_COMPATIBILITY = {
    "2.17": ["4.20", "4.21", "4.22"],
    "2.16": ["4.19", "4.20", "4.21", "4.22"],
    "2.15": ["4.18", "4.19", "4.20", "4.21"],
    "2.14": ["4.17", "4.18", "4.19", "4.20"],
    "2.13": ["4.16", "4.17", "4.18", "4.19"],
    "2.12": ["4.15", "4.16", "4.17", "4.18"],
    "2.11": ["4.14", "4.15", "4.16", "4.17"],
    "2.10": ["4.13", "4.14", "4.15", "4.16"],
    "2.9": ["4.12", "4.13", "4.14", "4.15"],
    "2.8": ["4.11", "4.12", "4.13", "4.14"],
    "2.7": ["4.10", "4.11", "4.12", "4.13"],
    "2.6": ["4.9", "4.10", "4.11", "4.12"],
    "2.5": ["4.8", "4.9", "4.10", "4.11"],
}


class ACMHealthCheck:
    """ACM must-gather health checker."""

    def __init__(self, must_gather_path: str, verbose: bool = False, debug: bool = False, mg_type: Optional[str] = None):
        """
        Initialize ACM health checker.

        Args:
            must_gather_path: Path to must-gather directory
            verbose: Enable verbose output
            debug: Enable debug output
            mg_type: Force must-gather type ('ACM' or 'OCP'), None for auto-detect
        """
        self.mg_path = Path(must_gather_path).absolute()
        self.verbose = verbose
        self.debug = debug

        # Find directories first (needed for validation)
        self.namespaces_dir = self._find_namespaces_dir()
        self.cluster_resources = self._find_cluster_resources()

        # Initialize OMC client early so we can use it for detection
        self.client = OMCClient(use=str(self.mg_path))

        # Detect or use forced must-gather type and cluster role using OMC
        if mg_type:
            self.mg_type = mg_type.upper()
            if self.debug:
                print(f"DEBUG: Forced must-gather type to: {self.mg_type}")
        else:
            self.mg_type = self._detect_mg_type()
            if self.debug:
                print(f"DEBUG: Auto-detected must-gather type: {self.mg_type}")

        self.is_hub = self._detect_hub_cluster()

        # Store ACM version for compatibility checking
        self.acm_version = None

    def _find_namespaces_dir(self) -> Optional[Path]:
        """Find the namespaces directory."""
        for path in self.mg_path.rglob("namespaces"):
            if path.is_dir():
                return path
        return None

    def _find_cluster_resources(self) -> Optional[Path]:
        """Find cluster-scoped-resources directory."""
        for path in self.mg_path.rglob("cluster-scoped-resources"):
            if path.is_dir():
                return path
        return None

    def _detect_mg_type(self) -> str:
        """Detect if this is ACM or OCP must-gather."""
        # Check for pods in open-cluster-management namespace using OMC
        try:
            pods = self.client.get_pods(namespace='open-cluster-management')
            if pods:
                return "ACM"
        except Exception:
            # Namespace doesn't exist or error getting pods
            pass
        return "OCP"

    def _detect_hub_cluster(self) -> bool:
        """Detect if this is a hub cluster."""
        # Check if open-cluster-management namespace exists using OMC
        try:
            namespace_obj = self.client.get(resource_type='namespace', name='open-cluster-management')
            return namespace_obj is not None
        except Exception:
            return False

    def print_header(self, text: str):
        """Print formatted header."""
        print(f"{Style.BRIGHT}{text}")

    def print_value(self, label: str, value: str, color: str = Fore.CYAN):
        """Print labeled value."""
        print(f"{Style.BRIGHT}{label}: {Style.RESET_ALL}{color}{value}")

    def print_pod_table_header(self):
        """Print pod table header in OMC style."""
        print(f"    {Style.BRIGHT}{'NAMESPACE':<40} {'NAME':<60} {'READY':<8} {'STATUS':<15} {'RESTARTS':<10}{Style.RESET_ALL}")

    def print_component_table_header(self):
        """Print component table header in OMC style."""
        print(f"    {Style.BRIGHT}{'NAME':<50} {'TYPE':<20} {'STATUS':<15}{Style.RESET_ALL}")

    def print_component_row(self, name: str, comp_type: str, status: str):
        """Print component in OMC-like table format with colors."""
        # Color based on status
        if status == "Available" or status == "True":
            status_color = Fore.GREEN
        elif status == "Progressing" or status == "Pending":
            status_color = Fore.YELLOW
        else:
            status_color = Fore.RED

        print(f"    {name:<50} {comp_type:<20} {status_color}{status:<15}{Style.RESET_ALL}")

    def print_pod_row(self, pod):
        """Print pod in OMC-like table format with colors."""
        # Calculate ready containers
        ready_count = 0
        total_count = len(pod.container_statuses) if pod.container_statuses else len(pod.containers)

        for cs in pod.container_statuses:
            if cs.get('ready', False):
                ready_count += 1

        ready_str = f"{ready_count}/{total_count}"

        # Get restart count
        restart_count = pod.get_restart_count()

        # Color based on status
        if pod.phase == "Running" and pod.is_ready():
            status_color = Fore.GREEN
        elif pod.phase in ["Succeeded", "Completed"]:
            status_color = Fore.GREEN
        elif pod.phase == "Pending":
            status_color = Fore.YELLOW
        else:
            status_color = Fore.RED

        # Color restart count
        if restart_count == 0:
            restart_color = Style.RESET_ALL
        elif restart_count <= 10:
            restart_color = Fore.YELLOW
        else:
            restart_color = Fore.RED

        # Color ready status
        if ready_count == total_count and total_count > 0:
            ready_color = Fore.GREEN
        elif ready_count > 0:
            ready_color = Fore.YELLOW
        else:
            ready_color = Fore.RED

        print(f"    {pod.namespace:<40} {pod.name:<60} {ready_color}{ready_str:<8}{Style.RESET_ALL} {status_color}{pod.phase:<15}{Style.RESET_ALL} {restart_color}{restart_count:<10}{Style.RESET_ALL}")

    def validate_must_gather(self) -> bool:
        """Validate that this is a valid must-gather."""
        if not self.namespaces_dir:
            print(f"{Fore.RED}Not a valid must-gather - namespaces directory not found")
            return False

        print(f"{Style.BRIGHT}Collecting environment details using must-gather:")
        print(f"{self.mg_path.name}\n")
        return True

    def check_acm_namespaces(self):
        """Check if all ACM namespaces are present."""
        required_ns = [
            "multicluster-engine",
            "open-cluster-management",
            "open-cluster-management-addon-observability",
            "open-cluster-management-agent",
            "open-cluster-management-agent-addon",
            "open-cluster-management-observability",
        ]

        missing = []
        for ns in required_ns:
            try:
                namespace_obj = self.client.get(resource_type='namespace', name=ns)
                if not namespace_obj:
                    missing.append(ns)
            except Exception:
                missing.append(ns)

        if not missing:
            status = f"{Fore.CYAN}All Present"
            self.print_value("Namespaces directory check", status)
        else:
            status = f"{Fore.RED}Some namespaces missing"
            self.print_value("Namespaces directory check", status)
            print(f"  {Fore.RED}Missing: {', '.join(missing)}")

        print()

    def get_versions(self):
        """Get ACM, MCE, or OCP version."""
        if self.debug:
            print(f"DEBUG get_versions: mg_type={self.mg_type}, is_hub={self.is_hub}")

        self.print_value("Must-Gather Image", self.mg_type)
        self.print_value("Hub Cluster", "Yes" if self.is_hub else "No")

        if self.mg_type == "ACM" and self.is_hub:
            # Get ACM version from subscription using OMC
            try:
                subscriptions = self.client.get(resource_type='subscription.operators.coreos.com', namespace='open-cluster-management')
                if self.debug:
                    print(f"DEBUG: Got {len(subscriptions) if isinstance(subscriptions, list) else 1} subscriptions")

                # Convert single subscription to list
                if not isinstance(subscriptions, list):
                    subscriptions = [subscriptions]

                # Find ACM subscription
                for sub in subscriptions:
                    # Check if this is the ACM subscription
                    spec = sub.spec
                    name = spec.get('name', '')
                    if self.debug:
                        print(f"DEBUG: Checking subscription: {sub.name}, spec.name={name}")

                    if 'advanced-cluster-management' in name.lower():
                        # Get installed CSV version
                        status = sub.status
                        installed_csv = status.get('installedCSV', '')
                        if self.debug:
                            print(f"DEBUG: Found ACM subscription, installedCSV={installed_csv}")

                        # Extract version from CSV name (format: advanced-cluster-management.vX.Y.Z)
                        match = re.search(r'v(\d+\.\d+\.\d+)', installed_csv)
                        if match:
                            version = match.group(1)
                            # Store for compatibility checking (major.minor only)
                            self.acm_version = '.'.join(version.split('.')[:2])
                            if self.debug:
                                print(f"DEBUG: Set acm_version to {self.acm_version}")
                            self.print_value("ACM Version", version)
                            break
                        else:
                            if self.debug:
                                print(f"DEBUG: Could not extract version from CSV: {installed_csv}")
                else:
                    self.print_value("ACM Version", "ACM subscription not found", Fore.RED)

            except Exception as e:
                if self.debug:
                    print(f"DEBUG: Error getting ACM version: {e}")
                self.print_value("ACM Version", f"Error: {e}", Fore.RED)

            # Get MCE version from subscription using OMC
            try:
                mce_subscriptions = self.client.get(resource_type='subscription.operators.coreos.com', namespace='multicluster-engine')

                # Convert single subscription to list
                if not isinstance(mce_subscriptions, list):
                    mce_subscriptions = [mce_subscriptions]

                # Find MCE subscription
                for sub in mce_subscriptions:
                    spec = sub.spec
                    name = spec.get('name', '')

                    if 'multicluster-engine' in name.lower() or 'multicluster' in name.lower():
                        # Get installed CSV version
                        status = sub.status
                        installed_csv = status.get('installedCSV', '')

                        # Extract version from CSV name
                        match = re.search(r'v(\d+\.\d+\.\d+)', installed_csv)
                        if match:
                            self.print_value("MCE Version", match.group(1))
                            break
            except Exception:
                pass  # MCE might not be installed
        else:
            # Get OCP version
            if self.cluster_resources:
                cv_file = self.cluster_resources / "config.openshift.io" / "clusterversions.yaml"
                if cv_file.exists():
                    cv = self._load_yaml_resource(cv_file)
                    if cv:
                        version = cv.get('status', {}).get('desired', {}).get('version')
                        if not version:
                            history = cv.get('status', {}).get('history', [])
                            if history:
                                version = history[0].get('version')
                        if version:
                            self.print_value("OCP Version", version)

    def check_environment_type(self):
        """Check if connected or disconnected environment."""
        # Check for registry-redhat-io directory
        registry_dirs = list(self.mg_path.rglob("registry-redhat-io*"))

        if registry_dirs:
            env_type = f"{Fore.CYAN}Connected"
        else:
            env_type = f"{Fore.YELLOW}Disconnected"

        self.print_value("Environment Type", env_type)
        print()

    def check_cluster_platform(self):
        """Get cluster platform."""
        if self.cluster_resources:
            infra_file = self.cluster_resources / "config.openshift.io" / "infrastructures.yaml"
            if infra_file.exists():
                infra = self._load_yaml_resource(infra_file)
                if infra:
                    platform = infra.get('status', {}).get('platform')
                    if not platform:
                        platform = infra.get('status', {}).get('platformStatus', {}).get('type')
                    if platform:
                        self.print_value("Cluster Platform", platform)

    def check_mch_health(self):
        """Check MultiClusterHub health."""
        mch_files = list(self.mg_path.rglob("multiclusterhubs/*.yaml"))

        if not mch_files:
            return

        mch_file = mch_files[0]
        data = yaml.safe_load(mch_file.read_text())

        status = data.get('status', {}) if data else {}
        spec = data.get('spec', {}) if data else {}

        current = str(status.get('currentVersion', 'Unknown'))
        desired = str(status.get('desiredVersion', 'Unknown'))
        phase = str(status.get('phase', 'Unknown'))
        backup = str(spec.get('enableClusterBackup', False)).lower()

        self.print_header("MCH Health:")

        # Version check
        if current == desired:
            print(f"    Current Version: {Fore.GREEN}{current}")
            print(f"    Desired Version: {Fore.GREEN}{desired}")
        else:
            print(f"    Current Version: {Fore.RED}{current}")
            print(f"    Desired Version: {Fore.RED}{desired}")

        # Phase check
        phase_color = Fore.GREEN if phase == "Running" else Fore.RED
        print(f"    Phase: {phase_color}{phase}")

        print(f"    Backup Enabled: {Fore.CYAN}{backup}")

        # Warning for backup with old versions
        if backup == "true" and self._version_compare(current, "2.5.0") <= 0:
            print(f"{Style.BRIGHT}{Fore.RED}    Warning!! Disable backup before upgrading to ACM 2.5")

        print()

    def _load_yaml_resource(self, filepath: Path):
        """Load a must-gather YAML file, handling both List and single-resource formats."""
        data = yaml.safe_load(filepath.read_text())
        if not data:
            return None
        if data.get('kind') == 'List':
            items = data.get('items', [])
            return items[0] if items else None
        return data

    def _count_key_occurrences(self, data, key: str) -> int:
        """Count how many times a key appears in a nested dict/list structure."""
        count = 0
        if isinstance(data, dict):
            if key in data:
                count += 1
            for v in data.values():
                count += self._count_key_occurrences(v, key)
        elif isinstance(data, list):
            for item in data:
                count += self._count_key_occurrences(item, key)
        return count

    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]

        try:
            return (normalize(v1) > normalize(v2)) - (normalize(v1) < normalize(v2))
        except ValueError:
            return 0

    def _check_ocp_acm_compatibility(self, ocp_version: str) -> tuple[bool, str]:
        """
        Check if OCP version is compatible with ACM version.

        Args:
            ocp_version: OCP version string (e.g., "4.14.8")

        Returns:
            Tuple of (is_compatible, message)
        """
        # Debug output
        if self.debug:
            print(f"DEBUG: ACM version: {self.acm_version}")
            print(f"DEBUG: OCP version input: {ocp_version}")

        if not self.acm_version:
            if self.debug:
                print("DEBUG: No ACM version set, skipping check")
            return True, ""

        # Extract major.minor from OCP version
        ocp_parts = ocp_version.split('.')
        if len(ocp_parts) < 2:
            if self.debug:
                print(f"DEBUG: Cannot parse OCP version: {ocp_version}")
            return True, "Unable to parse OCP version"

        ocp_minor = f"{ocp_parts[0]}.{ocp_parts[1]}"
        if self.debug:
            print(f"DEBUG: OCP minor version: {ocp_minor}")

        # Get supported versions for this ACM version
        supported_versions = ACM_OCP_COMPATIBILITY.get(self.acm_version)
        if self.debug:
            print(f"DEBUG: Supported versions for ACM {self.acm_version}: {supported_versions}")

        if not supported_versions:
            if self.debug:
                print(f"DEBUG: ACM {self.acm_version} not in compatibility matrix")
            return True, f"ACM {self.acm_version} not in compatibility matrix"

        # Check if OCP version is in supported list
        if ocp_minor in supported_versions:
            if self.debug:
                print(f"DEBUG: Version IS supported")
            return True, ""
        else:
            if self.debug:
                print(f"DEBUG: Version NOT supported!")
            # Not supported - show what versions are supported
            versions_str = ", ".join(supported_versions)
            return False, f"NOT supported by ACM {self.acm_version}. Supported: {versions_str}"

    def check_mce_health(self):
        """Check MultiCluster Engine health."""
        try:
            # Use OMC to get MCE resource
            mce = self.client.get(resource_type='multiclusterengine', name='multiclusterengine')

            if not mce:
                if self.debug:
                    print("DEBUG: MCE resource not found")
                return

            # Extract status information
            status = mce.status
            current = status.get('currentVersion', 'Unknown')
            desired = status.get('desiredVersion', 'Unknown')
            phase = status.get('phase', 'Unknown')

            # Get components info if available
            components = status.get('components', [])

            self.print_header("MCE Health:")

            # Version check
            if current == desired and current != 'Unknown':
                print(f"    Current Version: {Fore.GREEN}{current}")
                print(f"    Desired Version: {Fore.GREEN}{desired}")
            elif current == 'Unknown' or desired == 'Unknown':
                print(f"    Current Version: {Fore.YELLOW}{current}")
                print(f"    Desired Version: {Fore.YELLOW}{desired}")
            else:
                print(f"    Current Version: {Fore.RED}{current}")
                print(f"    Desired Version: {Fore.RED}{desired}")

            # Phase check
            phase_color = Fore.GREEN if phase == "Available" else Fore.RED
            print(f"    Phase: {phase_color}{phase}")

            # Show component status if verbose
            if self.verbose and components:
                print()
                print(f"    {Style.BRIGHT}Components:{Style.RESET_ALL}")
                self.print_component_table_header()
                for component in components:
                    comp_name = component.get('name', 'unknown')
                    comp_type = component.get('type', 'unknown')
                    comp_status = component.get('status', 'unknown')
                    self.print_component_row(comp_name, comp_type, comp_status)

            print()

        except Exception as e:
            if self.debug:
                print(f"DEBUG: Error getting MCE health: {e}")
            # MCE might not be installed, silently skip
            return

    def check_hub_details(self):
        """Get hub cluster details."""
        self.print_header("Hub Cluster Details:")

        # Find local-cluster managed cluster info
        mc_files = list(self.mg_path.rglob("managedclusters/local-cluster.yaml"))

        if not mc_files:
            print(f"    {Fore.RED}Cluster Details Not Available.\n")
            return

        mc_file = mc_files[0]
        mc = yaml.safe_load(mc_file.read_text()) or {}

        # Extract cluster name from API URL
        hub_name = "Unknown"
        client_configs = mc.get('spec', {}).get('managedClusterClientConfigs', [])
        if client_configs:
            api_url = client_configs[0].get('url', '')
            url_match = re.search(r'https://api\.([^.]+)\.', api_url)
            if url_match:
                hub_name = url_match.group(1)

        # Extract clusterID and openshiftVersion from labels
        labels = mc.get('metadata', {}).get('labels', {})
        cluster_id = str(labels.get('clusterID', 'Unknown'))
        ocp_version = str(labels.get('openshiftVersion', 'Unknown'))

        # Fallback to clusterClaims if labels didn't have the version
        if ocp_version == 'Unknown':
            for claim in mc.get('status', {}).get('clusterClaims', []):
                if claim.get('name') == 'version.openshift.io':
                    ocp_version = claim.get('value', 'Unknown')
                    break

        # Get more details from managedclusterinfo
        mci_files = list(self.mg_path.rglob("*/namespaces/local-cluster/*/managedclusterinfos/local-cluster.yaml"))

        if mci_files:
            mci = yaml.safe_load(mci_files[0].read_text()) or {}
            mci_status = mci.get('status', {})

            dist_info = mci_status.get('distributionInfo', {}).get('ocp', {})
            desired_version = str(dist_info.get('desiredVersion', 'Unknown'))
            cloud_vendor = str(mci_status.get('cloudVendor', 'Unknown'))

            # Count nodes by role from the managedcluster resource
            master_count = self._count_key_occurrences(mc, "node-role.kubernetes.io/master")
            worker_count = self._count_key_occurrences(mc, "node-role.kubernetes.io/worker")

            print(f"    Cluster Name: {Fore.CYAN}{hub_name}")
            print(f"    ClusterID: {Fore.CYAN}{cluster_id}")

            # Version comparison
            if ocp_version == desired_version:
                print(f"    OpenShift Version: {Fore.GREEN}{ocp_version}")
                print(f"    Desired Version: {Fore.GREEN}{desired_version}")
            else:
                print(f"    OpenShift Version: {Fore.RED}{ocp_version}")
                print(f"    Desired Version: {Fore.RED}{desired_version}")

            print(f"    Cluster Platform: {Fore.CYAN}{cloud_vendor}")
            print(f"    Control Plane Nodes: {Fore.CYAN}{master_count}")
            print(f"    Compute Nodes: {Fore.CYAN}{worker_count}")

        print()

    def check_managed_clusters(self):
        """Get managed clusters count and details."""
        self.print_header("Managed Clusters Details:")

        try:
            # Get all managed clusters using OMC
            managed_clusters = self.client.get(resource_type='managedclusters', all_namespaces=True)

            if isinstance(managed_clusters, list):
                count = len(managed_clusters)
            else:
                # Single cluster returned
                managed_clusters = [managed_clusters]
                count = 1

            print(f"    Number of Managed Clusters: {Fore.CYAN}{count}")

            # Check for unsupported versions (always, even without verbose)
            unsupported_clusters = []
            if count > 0:
                for cluster in managed_clusters:
                    name = cluster.name

                    # Get OCP version from clusterClaims
                    ocp_version = 'Unknown'
                    status = cluster.status or {}
                    cluster_claims = status.get('clusterClaims', [])
                    for claim in cluster_claims:
                        if claim.get('name') == 'version.openshift.io':
                            ocp_version = claim.get('value', 'Unknown')
                            break

                    # Check version compatibility
                    if ocp_version != 'Unknown':
                        is_compatible, compat_msg = self._check_ocp_acm_compatibility(ocp_version)
                        if not is_compatible:
                            unsupported_clusters.append((name, ocp_version, compat_msg))

            # Show warning about unsupported clusters (even without verbose)
            if unsupported_clusters and not self.verbose:
                print()
                print(f"    {Fore.RED}⚠ WARNING: {len(unsupported_clusters)} cluster(s) with unsupported OCP version:{Style.RESET_ALL}")
                for name, version, msg in unsupported_clusters:
                    print(f"      - {Style.BRIGHT}{name}{Style.RESET_ALL}: OCP {Fore.RED}{version}{Style.RESET_ALL} - {msg}")

            # Show details if verbose
            if self.verbose and count > 0:
                print()
                for cluster in managed_clusters:
                    name = cluster.name

                    # Get cluster status conditions
                    status = cluster.status or {}
                    conditions = status.get('conditions', [])
                    available = False
                    for condition in conditions:
                        if condition.get('type') == 'ManagedClusterConditionAvailable':
                            available = condition.get('status') == 'True'
                            break

                    # Get OCP version from clusterClaims
                    ocp_version = 'Unknown'
                    cluster_claims = status.get('clusterClaims', [])
                    for claim in cluster_claims:
                        if claim.get('name') == 'version.openshift.io':
                            ocp_version = claim.get('value', 'Unknown')
                            break

                    # Color based on availability
                    state_color = Fore.GREEN if available else Fore.RED
                    state = "Available" if available else "Unavailable"

                    print(f"    {Style.BRIGHT}{name}{Style.RESET_ALL}:")
                    print(f"      State: {state_color}{state}{Style.RESET_ALL}")

                    # Check version compatibility
                    if ocp_version != 'Unknown':
                        is_compatible, compat_msg = self._check_ocp_acm_compatibility(ocp_version)
                        version_color = Fore.CYAN if is_compatible else Fore.RED
                        print(f"      OCP Version: {version_color}{ocp_version}{Style.RESET_ALL}")

                        if not is_compatible:
                            print(f"      {Fore.RED}⚠ {compat_msg}{Style.RESET_ALL}")
                    else:
                        print(f"      OCP Version: {Fore.YELLOW}{ocp_version}{Style.RESET_ALL}")

                    print()

        except Exception as e:
            print(f"    {Fore.RED}Error getting managed clusters: {e}")

        print()

    def check_acm_pod_counts(self):
        """Check pod counts in ACM namespaces."""
        self.print_header("ACM Namespaces Pod Count:")

        acm_namespaces = [
            "open-cluster-management",
            "open-cluster-management-hub",
            "open-cluster-management-agent",
            "open-cluster-management-agent-addon",
            "open-cluster-management-observability",
            "open-cluster-management-addon-observability",
            "multicluster-engine",
        ]

        for ns in acm_namespaces:
            try:
                # First check if namespace exists
                namespace_obj = self.client.get(resource_type='namespace', name=ns)
                if not namespace_obj:
                    print(f"    {ns}: {Fore.YELLOW}N/A (namespace not found)")
                    continue

                # Use OMC library to get pods
                pods = self.client.get_pods(namespace=ns)
                count = len(pods)

                # Count running vs total
                running = sum(1 for p in pods if p.phase == "Running" and p.is_ready())
                error = sum(1 for p in pods if p.phase not in ["Running", "Succeeded", "Completed"])

                # Color based on health
                if count == 0:
                    color = Fore.RED
                    status = f"{color}{count}"
                elif error > 0:
                    color = Fore.RED
                    status = f"{color}{count} ({running} running, {error} error)"
                elif running < count:
                    color = Fore.YELLOW
                    status = f"{color}{count} ({running} running)"
                else:
                    color = Fore.CYAN
                    status = f"{color}{count}"

                print(f"    {ns}: {status}")
            except Exception as e:
                # Namespace might not exist in must-gather
                print(f"    {ns}: {Fore.YELLOW}N/A")

        print()

    def check_addon_status(self):
        """Check addon pod status."""
        self.print_header("Addons Status:")

        try:
            # Use OMC library to get pods
            pods = self.client.get_pods(namespace='open-cluster-management-agent-addon')

            if not pods:
                print(f"    {Fore.YELLOW}No addon pods found in open-cluster-management-agent-addon namespace\n")
                return

            # Display pods in table format
            self.print_pod_table_header()
            for pod in pods:
                self.print_pod_row(pod)

        except Exception as e:
            print(f"    {Fore.RED}Error getting addon pods: {e}")

        print()

    def check_klusterlet_status(self):
        """Check klusterlet pod status."""
        self.print_header("ACM Klusterlet Status:")

        try:
            # Use OMC library to get pods
            pods = self.client.get_pods(namespace='open-cluster-management-agent')

            if not pods:
                print(f"    {Fore.YELLOW}No klusterlet pods found in open-cluster-management-agent namespace\n")
                return

            # Display pods in table format
            self.print_pod_table_header()
            for pod in pods:
                self.print_pod_row(pod)

        except Exception as e:
            print(f"    {Fore.RED}Error getting klusterlet pods: {e}")

        print()

    def check_pods_error(self):
        """Check for pods in error state."""
        self.print_header("Pods in error state on cluster:")

        # Get all pods
        pods = self.client.get_pods(all_namespaces=True)

        # Find failing pods
        error_pods = [p for p in pods if p.phase not in ["Running", "Succeeded", "Completed"]]

        if error_pods:
            self.print_pod_table_header()
            for pod in error_pods:
                self.print_pod_row(pod)
        else:
            print(f"    {Fore.GREEN}No pods in error state")

        print()

        # Pods with high restarts
        self.print_header("Pods with restarts greater than 10 on cluster:")

        restart_pods = [p for p in pods if p.get_restart_count() > 10]

        if restart_pods:
            self.print_pod_table_header()
            for pod in restart_pods:
                self.print_pod_row(pod)
        else:
            print(f"    {Fore.GREEN}No pods with high restart counts")

        print()

    def check_etcd_status(self):
        """Check ETCD status."""
        self.print_header("ETCD Status:")

        # Run omc etcd status command
        try:
            output = self.client.execute(["etcd", "status"], output_format=None, parse=False)
            for line in output.split('\n'):
                if line.strip():
                    print(f"    {line}")
        except Exception as e:
            print(f"    {Fore.RED}Error getting ETCD status: {e}")

        print()

        self.print_header("ETCD Pods:")
        self.client.set_namespace("openshift-etcd")
        pods = self.client.get_pods(labels={"app": "etcd"})

        if pods:
            self.print_pod_table_header()
            for pod in pods:
                self.print_pod_row(pod)
        else:
            print(f"    {Fore.YELLOW}No ETCD pods found")

        print()

    def check_nodes(self):
        """Check cluster nodes."""
        self.print_header("Cluster Nodes:")

        nodes = self.client.get_nodes()

        for node in nodes:
            # Use the new __str__ method for nice formatted output
            print(f"{node}")

        print()

    def run_checks(self):
        """Run all appropriate checks based on cluster type."""
        if not self.validate_must_gather():
            return 1

        # Common checks
        self.get_versions()

        # Hub cluster checks
        if self.is_hub and self.mg_type == "ACM":
            self.check_environment_type()
            self.check_mch_health()
            self.check_mce_health()
            self.check_hub_details()
            self.check_acm_namespaces()
            self.check_managed_clusters()
            self.check_acm_pod_counts()
            self.check_addon_status()
            self.check_klusterlet_status()
            self.check_pods_error()

        # Managed cluster checks
        elif not self.is_hub and self.mg_type == "ACM":
            self.check_environment_type()
            self.check_addon_status()
            self.check_klusterlet_status()
            self.check_pods_error()

        # OCP cluster checks
        elif self.mg_type == "OCP":
            self.check_cluster_platform()
            self.check_environment_type()
            self.check_etcd_status()
            self.check_nodes()
            self.check_pods_error()

        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Red Hat Advanced Cluster Management must-gather archives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/must-gather
  %(prog)s ./must-gather-12345

This tool analyzes ACM, MCE, and OCP must-gather archives to provide
cluster health information, component status, and potential issues.
        """
    )

    parser.add_argument(
        "must_gather",
        help="Path to must-gather directory"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (show managed cluster details)"
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug output (show detailed diagnostic information)"
    )

    parser.add_argument(
        "-t", "--type",
        choices=["ACM", "OCP", "acm", "ocp"],
        metavar="TYPE",
        help="Force must-gather type (ACM or OCP) instead of auto-detection"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 2.1"
    )

    args = parser.parse_args()

    # Check if path exists
    if not Path(args.must_gather).exists():
        print(f"{Fore.RED}Error: Must-gather path does not exist: {args.must_gather}")
        return 1

    # Run health check
    try:
        checker = ACMHealthCheck(args.must_gather, verbose=args.verbose, debug=args.debug, mg_type=args.type)
        return checker.run_checks()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted by user")
        return 130
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

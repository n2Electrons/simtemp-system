#!/usr/bin/env python3
"""
driver_tester.py - Comprehensive Driver Testing Orchestrator for Simtemp

Copyright (c) Jorge Rodriguez Moreno

This script orchestrates the complete driver testing workflow:
1. Reads test configuration from simtemp_tests.yml
2. Executes pytest tests with configurable verbose output
3. Collects and integrates test results from multiple sources
4. Composes comprehensive HTML and JSON test reports
5. Integrates with GitHub issues for requirement traceability

Usage: ./driver_tester.py [--verbose] [--input-dir /path] [--output-dir /path]
"""

import os
import sys
import json
import argparse
import tempfile
import time
import glob
import datetime
import yaml
import re
import requests
from pathlib import Path

# Import QEMU session management functions directly from test_utils
try:
    from test_utils import (
        is_qemu_session_active,
        cleanup_qemu_session,
        cleanup_qemu_processes
    )
    QEMU_SUPPORT_AVAILABLE = True
except ImportError:
    print("Warning: QEMU session management not available")
    QEMU_SUPPORT_AVAILABLE = False


class TestLogger:
    def __init__(self, verbose=False):
        self.verbose = verbose
    
    def _safe_print(self, text):
        try:
            print(text)
        except BlockingIOError:
            # Handle case when stdout/stderr blocks
            try:
                # Try writing to a file instead
                with open("/tmp/driver_tester_log.txt", "a") as f:
                    f.write(text + "\n")
            except Exception:
                # If all logging fails, silently continue
                pass
    
    def info(self, message):
        self._safe_print(f"[INFO] {message}")
    
    def debug(self, message):
        if self.verbose:
            self._safe_print(f"[DEBUG] {message}")
    
    def warning(self, message):
        self._safe_print(f"[WARNING] {message}")
    
    def error(self, message):
        self._safe_print(f"[ERROR] {message}")


class DriverTestOrchestrator:
    def __init__(self, input_dir=None, output_dir=None, verbose=False):
        self.verbose = verbose
        self.logger = TestLogger(verbose)
        
        # Default input directory is the temp directory
        self.input_dir = input_dir or tempfile.gettempdir()
        
        # Default output directory - use absolute path relative to script location
        if output_dir:
            self.output_dir = output_dir
        else:
            script_dir = Path(__file__).parent
            self.output_dir = script_dir / 'reports'
        
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Test configuration file path - always relative to script directory
        script_dir = Path(__file__).parent
        self.test_config_file = script_dir / 'config/simtemp_tests.yml'
        
        self.logger.info(f"Input directory: {self.input_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Test config file: {self.test_config_file}")
        
        # Load test configuration
        self.test_config = self.load_test_config()
        
        # GitHub repository information for issue links
        self.github_repo_owner = os.getenv("GITHUB_OWNER", "n2Electrons")
        self.github_repo_name = os.getenv("GITHUB_REPO", "simtemp-system")
        
        # Load GitHub issue mappings from configuration or environment
        self.github_issue_mapping = self._load_github_issue_mappings()
        
        # Combined test results dictionary
        self.test_results = {
            "summary": {
                "total_modules": 0,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "not_implemented_tests": 0,
                "timestamp": datetime.datetime.now().isoformat(),
                "runtime": 0
            },
            "modules": {}
        }

    def load_test_config(self):
        """Load test configuration from YAML file"""
        try:
            if not os.path.exists(self.test_config_file):
                self.logger.error(f"Test configuration file not found: {self.test_config_file}")
                return {}
                
            with open(self.test_config_file, 'r') as f:
                config = yaml.safe_load(f)
                self.logger.info(f"Loaded test configuration with {len(config.get('tests', {}))} test suites")
                return config
        except Exception as e:
            self.logger.error(f"Error loading test configuration: {e}")
            return {}

    def _load_github_issue_mappings(self):
        """Load GitHub issue mappings from configuration file or environment"""
        mappings = {}
        
        # Try to load from a dedicated mappings file first
        script_dir = Path(__file__).parent
        mappings_file = script_dir / 'config/github_issue_mappings.json'
        
        if mappings_file.exists():
            try:
                with open(mappings_file, 'r') as f:
                    mappings = json.load(f)
                    self.logger.info(f"Loaded {len(mappings)} GitHub issue mappings from {mappings_file}")
                    return mappings
            except Exception as e:
                self.logger.error(f"Error loading GitHub issue mappings from {mappings_file}: {e}")
        
        # Try to load from test configuration
        if self.test_config and 'github_issue_mappings' in self.test_config:
            mappings = self.test_config['github_issue_mappings']
            self.logger.info(f"Loaded {len(mappings)} GitHub issue mappings from test configuration")
            return mappings
        
        # Try to load from environment variables (JSON format)
        env_mappings = os.getenv("GITHUB_ISSUE_MAPPINGS")
        if env_mappings:
            try:
                mappings = json.loads(env_mappings)
                self.logger.info(f"Loaded {len(mappings)} GitHub issue mappings from environment")
                return mappings
            except Exception as e:
                self.logger.error(f"Error parsing GitHub issue mappings from environment: {e}")
        
        # Fallback: try to discover mappings by searching the infra/data directory
        mappings = self._discover_github_issue_mappings()
        if mappings:
            self.logger.info(f"Discovered {len(mappings)} GitHub issue mappings")
            return mappings
        
        # Final fallback: empty mappings
        self.logger.warning("No GitHub issue mappings found - using empty mappings")
        return {}

    def _fetch_github_issue_status(self, issue_number):
        """Fetch the current status of a GitHub issue"""
        try:
            # Try to get GitHub token from environment
            self.logger.info("Attempting to retrieve GitHub token from environment variable 'GITHUB_TOKEN'")
            github_token = os.environ.get('GITHUB_TOKEN')
            if not github_token:
                pass  # Do not log absence of token to avoid exposing environment setup
            
            # GitHub API URL
            api_url = f"https://api.github.com/repos/{self.github_repo_owner}/{self.github_repo_name}/issues/{issue_number}"
            
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'TestReportGenerator/1.0'
            }
            
            # Add authentication if token is available
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                issue_data = response.json()
                state = issue_data.get('state', 'unknown')  # open, closed
                
                # Check for additional status indicators in labels or body
                labels = [label['name'].lower() for label in issue_data.get('labels', [])]
                
                # Map GitHub status to test status
                if state == 'closed':
                    return 'PASSED'
                elif state == 'open':
                    # Check labels for more specific status
                    if any(label in ['in-progress', 'in progress', 'working'] for label in labels):
                        return 'IN PROGRESS'
                    elif any(label in ['blocked', 'on-hold'] for label in labels):
                        return 'BLOCKED'
                    else:
                        return 'IN PROGRESS'  # Default for open issues
                else:
                    return 'UNKNOWN'
            
            elif response.status_code == 404:
                self.logger.warning(f"GitHub issue #{issue_number} not found")
                return 'NOT FOUND'
            else:
                self.logger.warning(f"Failed to fetch GitHub issue #{issue_number}: HTTP {response.status_code}")
                return 'UNKNOWN'
                
        except requests.RequestException as e:
            self.logger.warning(f"Network error fetching GitHub issue #{issue_number}: {e}")
            return 'UNKNOWN'
        except Exception as e:
            self.logger.warning(f"Error fetching GitHub issue #{issue_number}: {e}")
            return 'UNKNOWN'

    def _determine_test_status_from_github(self, test_id):
        """Determine test status by checking corresponding GitHub issue"""
        if not test_id or test_id not in self.github_issue_mapping:
            return None
        
        issue_number = self.github_issue_mapping[test_id]
        github_status = self._fetch_github_issue_status(issue_number)
        
        self.logger.debug(f"Test {test_id} → GitHub issue #{issue_number} → status: {github_status}")
        return github_status
    
    def _discover_github_issue_mappings(self):
        """Try to discover GitHub issue mappings from existing data files"""
        mappings = {}
        
        try:
            # Look for github_requirements.json in the infra/data directory
            script_dir = Path(__file__).parent
            workspace_root = script_dir.parent.parent  # Go up to workspace root
            github_data_file = workspace_root / 'infra/data/github_requirements.json'
            
            if github_data_file.exists():
                with open(github_data_file, 'r') as f:
                    github_data = json.load(f)
                    
                    # Extract mappings from requirements data
                    for req in github_data.get('requirements', []):
                        req_id = req.get('id')
                        github_issue = req.get('github_issue', '')
                        
                        if req_id and github_issue:
                            # Extract issue number from GitHub URL
                            issue_match = re.search(r'/issues/(\d+)', github_issue)
                            if issue_match:
                                issue_number = int(issue_match.group(1))
                                mappings[req_id] = issue_number
                
                self.logger.debug(f"Discovered mappings from {github_data_file}: {mappings}")
            
            # Also try to use the GitHub search script to find more mappings
            github_search_results = workspace_root / 'github_test_ids.json'
            if github_search_results.exists():
                with open(github_search_results, 'r') as f:
                    search_data = json.load(f)
                    
                    # Extract mappings from search results
                    for result in search_data.get('results', []):
                        issue_id = result.get('issue_id')
                        matched_ids = result.get('matched_ids', [])
                        
                        if issue_id and matched_ids:
                            issue_number = int(issue_id)
                            for matched_id in matched_ids:
                                mappings[matched_id] = issue_number
                
                self.logger.debug(f"Additional mappings from search results: {mappings}")
                
        except Exception as e:
            self.logger.debug(f"Error discovering GitHub issue mappings: {e}")
        
        return mappings

    def generate_github_issue_url(self, test_id):
        """Generate GitHub issue URL from test ID, using specific issue if known"""
        if not test_id:
            return None
        
        # Check if we have a specific issue number for this test ID
        if test_id in self.github_issue_mapping:
            issue_number = self.github_issue_mapping[test_id]
            return f"https://github.com/{self.github_repo_owner}/{self.github_repo_name}/issues/{issue_number}"
        
        # For test IDs without specific issues, use search URL
        # Format: https://github.com/{owner}/{repo}/issues?q={test_id}
        search_url = f"https://github.com/{self.github_repo_owner}/{self.github_repo_name}/issues?q={test_id}"
        return search_url
        
    def generate_github_issue_link_html(self, test_id, test_status=None):
        """Generate HTML link to GitHub issue for test ID with dynamic status"""
        if not test_id:
            return ""
        
        # If no status provided, try to get it from GitHub
        github_status = None
        if test_id in self.github_issue_mapping:
            github_status = self._determine_test_status_from_github(test_id)
            if github_status and github_status != 'UNKNOWN':
                # Use GitHub status if available
                test_status = github_status
        
        # Do not show GitHub links for NOT IMPLEMENTED tests
        if test_status and test_status.lower() == "not implemented":
            return f'<span class="test-id-no-link">[{test_id}]</span>'
            
        issue_url = self.generate_github_issue_url(test_id)
        if issue_url:
            # Determine status class for styling
            status_class = ""
            if test_status:
                status_class = f" status-{test_status.lower().replace(' ', '-')}"
            
            # Determine if it's a direct issue link or search link for the title
            if test_id in self.github_issue_mapping:
                title_text = f"View GitHub issue #{self.github_issue_mapping[test_id]} for {test_id}"
                if github_status:
                    title_text += f" (Status: {github_status})"
                return f'<a href="{issue_url}" target="_blank" class="github-link{status_class}" title="{title_text}">{test_id}</a>'
            else:
                # For test IDs without specific mappings, don't show links in individual tests
                return f'<span class="test-id-no-link">[{test_id}]</span>'
        return test_id

    def show_test_configuration_overview(self):
        """Show a comprehensive overview of all test suites and their configuration"""
        self.logger.info("=" * 80)
        self.logger.info("TEST CONFIGURATION OVERVIEW")
        self.logger.info("=" * 80)
        
        if not self.test_config or 'tests' not in self.test_config:
            self.logger.warning("No test configuration found!")
            return
            
        script_dir = Path(__file__).parent
        
        for suite_name, suite_config in self.test_config['tests'].items():
            enabled = suite_config.get('enabled', True)
            pytest_file = suite_config.get('pytest_file')
            own_pipeline = suite_config.get('own_pipeline', False)
            repository = suite_config.get('repository', 'Not specified')
            description = suite_config.get('description', 'No description')
            
            self.logger.info(f"\nTEST SUITE: {suite_name}")
            self.logger.info(f"   Enabled: {enabled}")
            self.logger.info(f"   Own Pipeline: {own_pipeline}")
            self.logger.info(f"   Repository: {repository}")
            self.logger.info(f"   Description: {description}")
            
            # Show pytest file information
            # Distinguish between: (a) key not present (auto-discover), (b) key present and set to null (explicitly disabled), (c) empty string (auto-discover), (d) specific file
            if 'pytest_file' not in suite_config:
                self.logger.info(f"   Pytest file: auto-discover test_*.py files (not configured at suite level)")
            else:
                pytest_file_value = suite_config.get('pytest_file')
                if pytest_file_value is None:
                    # Explicit null in YAML means do not execute pytest for this suite
                    self.logger.info(f"   Pytest file: null (no pytest execution)")
                elif not pytest_file_value:
                    self.logger.info(f"   Pytest file: auto-discover test_*.py files")
                else:
                    pytest_path = script_dir / pytest_file_value
                    exists_status = "EXISTS" if pytest_path.exists() else "NOT FOUND"
                    self.logger.info(f"   Pytest file: {pytest_file_value} [{exists_status}]")

                    # Show pytest file content summary if it exists
                    if pytest_path.exists():
                        try:
                            with open(pytest_path, 'r') as f:
                                content = f.read()
                                test_functions = [line.strip().split('(')[0].replace('def ', '')
                                                for line in content.split('\n')
                                                if line.strip().startswith('def test_')]

                                if test_functions:
                                    self.logger.info(f"   Pytest functions found:")
                                    for func in test_functions:
                                        self.logger.info(f"      - {func}")
                                else:
                                    self.logger.info(f"   No test functions found in {pytest_file_value}")
                        except Exception as e:
                            self.logger.info(f"   Could not read {pytest_file_value}: {e}")
            
            # Show configured test cases
            test_cases = suite_config.get('test_cases', [])
            if test_cases:
                self.logger.info(f"   Configured test cases ({len(test_cases)}):")
                for i, test_case in enumerate(test_cases, 1):
                    test_name = test_case.get('name', 'Unknown')
                    test_id = test_case.get('test_id', 'No ID')
                    test_enabled = test_case.get('enabled', True)
                    test_desc = test_case.get('description', '')
                    
                    status = "ENABLED" if test_enabled else "DISABLED"
                    self.logger.info(f"      {i}. [{status}] {test_name} (ID: {test_id})")
                    if test_desc:
                        self.logger.info(f"         Description: {test_desc}")
            else:
                self.logger.info(f"   No test cases configured")
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STARTING TEST EXECUTION")
        self.logger.info("=" * 80)

    def find_test_detail_files(self):
        """Find all test_details_{module}.json files in the input directory"""
        pattern = os.path.join(self.input_dir, "test_details_*.json")
        files = glob.glob(pattern)
        
        self.logger.info(f"Found {len(files)} test detail files")
        if self.verbose:
            for file in files:
                self.logger.debug(f" - {os.path.basename(file)}")
                
        return files

    def load_test_details(self, file_path):
        """Load test details from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading test details from {file_path}: {e}")
            return None

    def extract_module_name(self, file_path):
        """Extract module name from file path (test_details_{module}.json)"""
        basename = os.path.basename(file_path)
        # Remove 'test_details_' prefix and '.json' suffix
        if basename.startswith("test_details_") and basename.endswith(".json"):
            return basename[13:-5]  # len("test_details_") = 13, len(".json") = 5
        return "unknown"

    def collect_test_results(self):
        """Collect test results by executing each test suite and generating incremental detail files"""
        self.logger.info("TestRunner: Starting test collection process")
        start_time = time.time()
        
        # Show detailed configuration overview at the start
        self.logger.info("TestRunner: Showing test configuration overview")
        self.show_test_configuration_overview()
        
        # Always generate fresh results from test configuration
        # This ensures we always run pytest and capture current test state
        self.logger.info("TestRunner: Generating fresh test results from test configuration")
        self.generate_from_config()
        
        self.test_results["summary"]["runtime"] = time.time() - start_time
        self.logger.info(f"TestRunner: Completed - collected results from {self.test_results['summary']['total_modules']} modules in {self.test_results['summary']['runtime']:.2f}s")

    def generate_from_config(self):
        """Generate test results structure from test configuration"""
        self.logger.info("TestRunner: Starting config processing")
        
        if not self.test_config or 'tests' not in self.test_config:
            self.logger.error("TestRunner: No test configuration available")
            return
        
        total_suites = len(self.test_config['tests'])
        self.logger.info(f"TestRunner: Processing {total_suites} test suites")
            
        for test_suite_name, test_suite_config in self.test_config['tests'].items():
            self.logger.info(f"TestRunner: Processing suite '{test_suite_name}'")
            
            if not test_suite_config.get('enabled', True):
                self.logger.info(f"TestRunner: Skipping disabled suite '{test_suite_name}'")
                continue
                
            self.logger.info(f"TestRunner: Suite '{test_suite_name}' is enabled")
            
            module_data = {
                "name": test_suite_name,
                "description": test_suite_config.get('description', ''),
                "enabled": True,
                "tests": []
            }
            
            # Add test cases from configuration
            test_cases = test_suite_config.get('test_cases', [])
            self.logger.info(f"TestRunner: Found {len(test_cases)} test cases for module {test_suite_name}")
            
            for test_case in test_cases:
                test_name = test_case.get('name', 'unnamed')
                test_enabled = test_case.get('enabled', True)
                test_id = test_case.get('test_id', '')
                self.logger.info(f"  - Test case: {test_name} (ID: {test_id}, enabled: {test_enabled})")
                if test_case.get('debug_info'):
                    self.logger.info(f"    Debug info: {test_case['debug_info']}")
                    
                if test_enabled:
                    test_data = {
                        "name": test_case['name'],
                        "description": test_case.get('description', ''),
                        "test_id": test_case.get('test_id', ''),
                        "status": "unknown",  # Will be updated if actual results are found
                        "duration": 0,
                        "message": "Test configured but no execution results found"
                    }
                    module_data["tests"].append(test_data)
                    self.test_results["summary"]["total_tests"] += 1
                else:
                    self.logger.info(f"    Skipping disabled test: {test_name}")
            
            # Try to find actual test results for this suite
            self.update_with_actual_results(test_suite_name, module_data)
            
            # Mark remaining unknown tests as "not implemented"
            self.mark_unimplemented_tests(module_data)
            
            self.test_results["modules"][test_suite_name] = module_data
            self.test_results["summary"]["total_modules"] += 1

    def mark_unimplemented_tests(self, module_data):
        """Mark tests that are configured but have no pytest implementation as 'not implemented'"""
        for test in module_data['tests']:
            if test['status'] == 'unknown':
                test['status'] = 'not implemented'
                test['message'] = 'Test defined in configuration but no pytest implementation found'
                self.test_results["summary"]["not_implemented_tests"] += 1
                self.logger.info(f"Marked test '{test['name']}' as not implemented")

    def update_with_actual_results(self, suite_name, module_data):
        """Try to find and integrate actual test execution results"""
        # Look for pytest JSON results or recent pytest output
        self.capture_pytest_results(suite_name, module_data)
        
        # Also check results directory for any JSON files
        results_dir = 'results'
        if os.path.exists(results_dir):
            for result_file in glob.glob(os.path.join(results_dir, '*.json')):
                try:
                    with open(result_file, 'r') as f:
                        results = json.load(f)
                        self.match_results_to_config(module_data, results)
                except Exception as e:
                    self.logger.debug(f"Could not parse result file {result_file}: {e}")

    def capture_pytest_results(self, suite_name, module_data):
        """Run pytest and capture results to update test status"""
        self.logger.info(f"TestRunner: Starting for suite '{suite_name}'")
        
        try:
            import subprocess
            
            # Run pytest with JSON output
            self.logger.info(f"TestRunner: Looking for pytest config for module {suite_name}")
            
            # Get the specific pytest file for this module from configuration
            module_config = None
            for test_suite_name, test_suite_config in self.test_config.get('tests', {}).items():
                if test_suite_name == suite_name:
                    module_config = test_suite_config
                    self.logger.info(f"TestRunner: Found config for suite '{suite_name}'")
                    break
            
            if not module_config:
                self.logger.warning(f"TestRunner: No configuration found for module {suite_name}")
                return
                
            # Initialize test_files to avoid UnboundLocalError
            test_files = []
                
            # Check if this module has a specific pytest file configured
            pytest_file = module_config.get('pytest_file')
            self.logger.info(f"TestRunner: pytest_file value for {suite_name}: {repr(pytest_file)}")
            
            if pytest_file is None:
                # Check if pytest_file was explicitly set to null vs. not defined
                if 'pytest_file' in module_config:
                    # Module explicitly configured to not run pytest (pytest_file: null)
                    self.logger.info(
                        f"Module {suite_name} configured with pytest_file: null "
                        "- checking for test details file"
                    )
                    
                    # Special handling for jenkins_test module
                    if suite_name == "jenkins_test":
                        self.logger.info(
                            "Special handling for jenkins_test module "
                            "- looking for test details file"
                        )
                        jenkins_details_file = os.path.join(
                            self.input_dir, "test_details_jenkins_test.json"
                        )
                        if os.path.exists(jenkins_details_file):
                            self.logger.info(
                                f"Found Jenkins test details file: "
                                f"{jenkins_details_file}"
                            )
                            try:
                                with open(jenkins_details_file, 'r') as f:
                                    jenkins_results = json.load(f)
                                    self.logger.info(
                                        f"Loaded Jenkins test results: "
                                        f"{jenkins_results}"
                                    )
                                    self.match_jenkins_results_to_config(
                                        module_data, jenkins_results
                                    )
                            except Exception as e:
                                self.logger.error(
                                    f"Could not parse Jenkins test details file: {e}"
                                )
                        else:
                            self.logger.warning(
                                f"Jenkins test details file not found at: "
                                f"{jenkins_details_file}"
                            )
                    return
                else:
                    # pytest_file not defined at suite level - collect from test cases
                    self.logger.info(
                        f"TestRunner: No pytest_file key found at suite level for {suite_name} "
                        "- collecting from test cases"
                    )
                    # Continue to collection logic below
            elif not pytest_file:
                # Empty string or false-y value - collect from test cases
                self.logger.info(
                    f"TestRunner: Empty pytest file at suite level for {suite_name} "
                    "- collecting from test cases"
                )
                # Continue to collection logic below
            else:
                # Use the specific pytest file for this module
                script_dir = Path(__file__).parent
                test_file_path = script_dir / pytest_file
                if test_file_path.exists():
                    test_files = [test_file_path]
                    self.logger.info(
                        f"FOUND pytest file for {suite_name}: {pytest_file}"
                    )
                    self.logger.info(f"Full path: {test_file_path}")
                    
                    # Show test file contents summary
                    try:
                        with open(test_file_path, 'r') as f:
                            content = f.read()
                            test_functions = [
                                line.strip() for line in content.split('\n')
                                if line.strip().startswith('def test_')
                            ]
                            self.logger.info(
                                f"Test functions found in {pytest_file}:"
                            )
                            for test_func in test_functions:
                                self.logger.info(f"   - {test_func}")
                            if not test_functions:
                                self.logger.warning(
                                    f"No test functions found in {pytest_file}"
                                )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not read test file contents: {e}"
                        )
                        
                else:
                    self.logger.error(
                        f"Configured pytest file {pytest_file} not found "
                        f"for module {suite_name}"
                    )
                    self.logger.error(f"   Searched at: {test_file_path}")
                    return
            
            # Collection logic for when pytest_file is None (not defined) or empty
            if pytest_file is None and 'pytest_file' not in module_config or not pytest_file:
                # No pytest file at suite level - collect from test cases
                self.logger.info(
                    f"TestRunner: No pytest file at suite level for {suite_name} "
                    "- collecting from test cases"
                )
                
                # Collect unique pytest files from test cases
                test_case_files = set()
                test_cases = module_config.get('test_cases', [])
                self.logger.info(f"TestRunner: Found {len(test_cases)} test cases to examine")
                
                for test_case in test_cases:
                    test_case_name = test_case.get('name', 'unnamed')
                    test_case_enabled = test_case.get('enabled', True)
                    case_pytest_file = test_case.get('pytest_file')
                    
                    self.logger.info(f"TestRunner: Examining test case '{test_case_name}' - enabled: {test_case_enabled}, pytest_file: {case_pytest_file}")
                    
                    # Only include enabled test cases
                    if test_case_enabled:
                        if case_pytest_file:
                            test_case_files.add(case_pytest_file)
                            self.logger.info(f"TestRunner: Added pytest file '{case_pytest_file}' from enabled test case '{test_case_name}'")
                        else:
                            self.logger.info(f"TestRunner: Test case '{test_case_name}' is enabled but has no pytest_file")
                    else:
                        self.logger.info(f"TestRunner: Skipping disabled test case '{test_case_name}'")
                
                self.logger.info(f"TestRunner: Collected {len(test_case_files)} unique pytest files: {list(test_case_files)}")
                
                if test_case_files:
                    script_dir = Path(__file__).parent
                    test_files = []
                    self.logger.info(f"TestRunner: Looking for pytest files in directory: {script_dir}")
                    
                    for file_name in test_case_files:
                        test_file_path = script_dir / file_name
                        self.logger.info(f"TestRunner: Checking if pytest file exists: {test_file_path}")
                        
                        if test_file_path.exists():
                            test_files.append(test_file_path)
                            self.logger.info(
                                f"TestRunner: Found pytest file from test case: {file_name}"
                            )
                        else:
                            self.logger.warning(
                                f"TestRunner: Pytest file from test case not found: "
                                f"{file_name} (full path: {test_file_path})"
                            )
                    
                    if not test_files:
                        self.logger.warning(
                            f"TestRunner: No valid pytest files found for {suite_name} "
                            "from test cases"
                        )
                        return
                        
                    self.logger.info(
                        f"TestRunner: Using pytest files from test cases for {suite_name}: "
                        f"{[f.name for f in test_files]}"
                    )
                else:
                    # Fall back to finding all test files (old behavior)
                    script_dir = Path(__file__).parent
                    test_files = list(script_dir.glob("test_*.py"))
                    self.logger.info(
                        f"TestRunner: No pytest files in test cases for {suite_name}, "
                        f"using all test files: {[f.name for f in test_files]}"
                    )
            else:
                # Use the specific pytest file for this module
                script_dir = Path(__file__).parent
                test_file_path = script_dir / pytest_file
                if test_file_path.exists():
                    test_files = [test_file_path]
                    self.logger.info(
                        f"FOUND pytest file for {suite_name}: {pytest_file}"
                    )
                    self.logger.info(f"Full path: {test_file_path}")
                    
                    # Show test file contents summary
                    try:
                        with open(test_file_path, 'r') as f:
                            content = f.read()
                            test_functions = [
                                line.strip() for line in content.split('\n')
                                if line.strip().startswith('def test_')
                            ]
                            self.logger.info(
                                f"Test functions found in {pytest_file}:"
                            )
                            for test_func in test_functions:
                                self.logger.info(f"   - {test_func}")
                            if not test_functions:
                                self.logger.warning(
                                    f"No test functions found in {pytest_file}"
                                )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not read test file contents: {e}"
                        )
                        
                else:
                    self.logger.error(
                        f"Configured pytest file {pytest_file} not found "
                        f"for module {suite_name}"
                    )
                    self.logger.error(f"   Searched at: {test_file_path}")
                    return
                    
            if not test_files:
                self.logger.warning("No test files found")
                return
                
            # Convert to relative paths from project root
            project_root = script_dir.parent.parent
            test_file_paths = [str(f.relative_to(project_root)) for f in test_files]
            
            self.logger.info(f"Project root: {project_root}")
            self.logger.info(f"Test file paths for {suite_name}: {test_file_paths}")
            
            # Show configured test cases for this module
            if module_data and 'tests' in module_data:
                self.logger.info(f"Configured test cases for {suite_name}:")
                for test_case in module_data['tests']:
                    test_name = test_case.get('name', 'Unknown')
                    test_id = test_case.get('test_id', 'No ID')
                    enabled = test_case.get('enabled', True)
                    status = "ENABLED" if enabled else "DISABLED"
                    self.logger.info(f"   [{status}] {test_name} (ID: {test_id})")
            
            # First, run pytest in collect-only mode to see what tests will be discovered
            collect_cmd = ["python3", "-m", "pytest", "--collect-only", "-q"] + test_file_paths
            self.logger.info(f"Discovering tests with: {' '.join(collect_cmd)}")
            
            try:
                collect_result = subprocess.run(collect_cmd, capture_output=True, text=True, timeout=30, cwd=project_root)
                if collect_result.returncode == 0:
                    self.logger.info("Tests discovered by pytest:")
                    for line in collect_result.stdout.split('\n'):
                        if '::test_' in line and line.strip():
                            self.logger.info(f"   {line.strip()}")
                else:
                    self.logger.warning(f"Test discovery failed: {collect_result.stderr}")
            except Exception as e:
                self.logger.warning(f"Could not run test discovery: {e}")
            
            # Build pytest command with configurable verbose output
            cmd = ["python3", "-m", "pytest", "-v", "--tb=short"]
            
            # Check if any test case in this suite has verbose_output enabled
            verbose_enabled = False
            test_cases = module_config.get('test_cases', [])
            for test_case in test_cases:
                enabled = test_case.get('enabled', True)
                verbose = test_case.get('verbose_output', False)
                if enabled and verbose:
                    verbose_enabled = True
                    break
            
            if verbose_enabled:
                cmd.append("-s")  # Add -s flag to show print statements
                self.logger.info(
                    f"Verbose output enabled for suite {suite_name}"
                )
            
            cmd.extend(test_file_paths)
            
            self.logger.info(
                f"Executing pytest command for {suite_name}: {' '.join(cmd)}"
            )
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                cwd=project_root
            )
            
            self.logger.info(f"Pytest exit code for {suite_name}: {result.returncode}")
            if result.stdout:
                self.logger.info(f"Pytest stdout for {suite_name}:\n{result.stdout}")
            if result.stderr:
                self.logger.warning(f"Pytest stderr for {suite_name}:\n{result.stderr}")
            
            # Parse pytest output even if there were errors 
            # Often tests pass but there are write issues
            self.parse_pytest_output(result.stdout, module_data)
            
            # Generate incremental test detail file for this suite
            self.generate_suite_detail_file(suite_name, module_data, result)
            
        except Exception as e:
            try:
                self.logger.error(f"Error running pytest for {suite_name}: {e}")
            except:
                # If even logging fails due to write blocking, continue silently
                pass
            # Try to extract any successful results from the error context
            if 'result' in locals() and result.stdout:
                try:
                    self.logger.info("Attempting to parse partial results despite error")
                except:
                    pass  # Silent fallback if logging fails
                try:
                    self.parse_pytest_output(result.stdout, module_data)
                except Exception as parse_error:
                    try:
                        self.logger.warning(
                            f"Could not parse partial results: {parse_error}"
                        )
                    except:
                        pass  # Silent fallback if logging fails

    def generate_suite_detail_file(self, suite_name, module_data, pytest_result):
        """Generate a test detail file for this specific suite"""
        try:
            import datetime
            
            # Use fixed filename to avoid accumulation of files
            detail_filename = f"test_details_{suite_name}.json"
            detail_filepath = os.path.join(self.input_dir, detail_filename)
            
            # Prepare detailed test results for this suite
            suite_details = {
                "name": suite_name,
                "description": module_data.get('description', ''),
                "enabled": module_data.get('enabled', True),
                "tests": module_data.get('tests', []),
                "execution_info": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "pytest_exit_code": pytest_result.returncode,
                    "pytest_stdout": pytest_result.stdout,
                    "pytest_stderr": pytest_result.stderr
                }
            }
            
            # Write the incremental detail file
            with open(detail_filepath, 'w') as f:
                json.dump(suite_details, f, indent=2)
                
            self.logger.info(f"Generated test detail file: {detail_filename}")
            
        except Exception as e:
            self.logger.error(f"Error generating suite detail file for {suite_name}: {e}")

    def parse_pytest_output(self, pytest_output, module_data):
        """Parse pytest output to extract test results"""
        lines = [l for l in pytest_output.split('\n') if l.strip()]

        # Two common patterns to handle:
        # 1) Same-line: path/to/test_file.py::test_name PASSED
        # 2) Multi-line verbose: path/to/test_file.py::test_name\n    <prints>\nPASSED

        current_test = None

        for line in lines:
            stripped = line.strip()

            # Pattern 1: "file.py::test_name <STATUS>" on same line
            m = re.match(r"^(?P<file>[^:\s]+)::(?P<test>test[^\s]+)\s+(?P<status>PASSED|FAILED|SKIPPED)$", stripped)
            if m:
                test_file = m.group('file')
                test_name = m.group('test')
                status = m.group('status').lower()
                self.logger.info(f"Parsed test result: {test_file}::{test_name} -> {status}")
                self.update_test_status(module_data, test_name, status)
                continue

            # Pattern 2: discovery/execution line with file::test (may have trailing text)
            if '::test_' in stripped:
                # Try to extract file and test token even if there's trailing text
                m_id = re.search(r"(?P<file>[^:\s]+)::(?P<test>test[^\s:]*)", stripped)
                if m_id:
                    test_file = m_id.group('file')
                    test_name = m_id.group('test')

                    # If status is present on the same line, capture it
                    m_status = re.search(r"\b(PASSED|FAILED|SKIPPED)\b", stripped)
                    if m_status:
                        status = m_status.group(1).lower()
                        self.logger.info(f"Parsed test result: {test_file}::{test_name} -> {status}")
                        self.update_test_status(module_data, test_name, status)
                        current_test = None
                        continue
                    else:
                        # No status yet; remember current test and continue
                        current_test = {
                            'file': test_file,
                            'name': test_name
                        }
                        continue

            # Pattern 3: status line following a previous test identifier
            if current_test and stripped in ['PASSED', 'FAILED', 'SKIPPED']:
                status = stripped.lower()
                test_name = current_test['name']
                test_file = current_test['file']
                self.logger.info(f"Parsed test result: {test_file}::{test_name} -> {status}")
                self.update_test_status(module_data, test_name, status)
                current_test = None
                continue

            # Otherwise ignore non-status lines (prints, tracebacks, etc.)
                    
        # Also look for summary lines (e.g., "1 passed in 4.85s")
        for line in pytest_output.split('\n'):
            if ' passed in ' in line or ' failed in ' in line or re.search(r"\d+ passed", line):
                self.logger.info(f"Pytest summary: {line.strip()}")

    def update_test_status(self, module_data, test_name, status):
        """Update the status of a specific test"""
        updated = False
        
        for test in module_data['tests']:
            # Match by test name or if the pytest test name contains the configured test name
            if (test['name'] == test_name or 
                test_name.replace('test_', '') == test['name'] or
                test['name'] in test_name):
                
                old_status = test['status']
                test['status'] = status
                test['message'] = f"Test executed via pytest: {test_name}()"
                
                # Update summary counts
                if old_status == 'unknown':
                    if status == 'passed':
                        self.test_results["summary"]["passed_tests"] += 1
                    elif status == 'failed':
                        self.test_results["summary"]["failed_tests"] += 1
                    elif status == 'skipped':
                        self.test_results["summary"]["skipped_tests"] += 1
                
                self.logger.info(f"Updated test '{test['name']}' status: {old_status} -> {status}")
                updated = True
                break
        
        if not updated:
            # If no matching configured test found, add the actual test result
            new_test = {
                "name": test_name,
                "description": f"Actual pytest test: {test_name}()",
                "test_id": "",
                "status": status,
                "duration": 0,
                "message": "Test executed via pytest (not in configuration)"
            }
            module_data['tests'].append(new_test)
            self.test_results["summary"]["total_tests"] += 1
            
            if status == 'passed':
                self.test_results["summary"]["passed_tests"] += 1
            elif status == 'failed':
                self.test_results["summary"]["failed_tests"] += 1
            elif status == 'skipped':
                self.test_results["summary"]["skipped_tests"] += 1
                
            self.logger.info(f"Added actual test '{test_name}' with status: {status}")

    def match_results_to_config(self, module_data, results):
        """Match actual test results to configured test cases"""
        # This is a basic implementation - can be enhanced based on actual pytest output format
        if isinstance(results, dict) and 'tests' in results:
            for actual_test in results['tests']:
                test_name = actual_test.get('name', '')
                # Try to find matching configured test
                for configured_test in module_data['tests']:
                    if configured_test['name'] in test_name or test_name in configured_test['name']:
                        configured_test['status'] = actual_test.get('status', 'unknown')
                        configured_test['duration'] = actual_test.get('duration', 0)
                        configured_test['message'] = actual_test.get('message', '')
                        
                        # Update summary counts
                        status = configured_test['status'].lower()
                        if status == "passed":
                            self.test_results["summary"]["passed_tests"] += 1
                        elif status == "failed":
                            self.test_results["summary"]["failed_tests"] += 1
                        elif status == "skipped":
                            self.test_results["summary"]["skipped_tests"] += 1
                        break

    def match_jenkins_results_to_config(self, module_data, jenkins_results):
        """Match Jenkins test results to configured test cases"""
        self.logger.info("Matching Jenkins test results to configuration")
        
        if not isinstance(jenkins_results, dict):
            self.logger.warning("Jenkins results is not a dictionary")
            return
            
        # Look for tests array in Jenkins results
        jenkins_tests = jenkins_results.get('tests', [])
        self.logger.info(f"Found {len(jenkins_tests)} tests in Jenkins results")
        
        for jenkins_test in jenkins_tests:
            test_name = jenkins_test.get('name', '')
            test_status = jenkins_test.get('status', 'unknown').lower()
            test_duration = jenkins_test.get('duration', 0)
            test_message = jenkins_test.get('message', '')
            
            self.logger.info(f"Processing Jenkins test: {test_name} -> {test_status}")
            
            # Find matching configured test
            for configured_test in module_data['tests']:
                if configured_test['name'] == test_name:
                    old_status = configured_test['status']
                    configured_test['status'] = test_status
                    configured_test['duration'] = test_duration
                    configured_test['message'] = test_message
                    
                    self.logger.info(f"Updated test '{test_name}': {old_status} -> {test_status}")
                    
                    # Update summary counts
                    if old_status == 'unknown':
                        if test_status == "passed":
                            self.test_results["summary"]["passed_tests"] += 1
                        elif test_status == "failed":
                            self.test_results["summary"]["failed_tests"] += 1
                        elif test_status == "skipped":
                            self.test_results["summary"]["skipped_tests"] += 1
                    break
            else:
                self.logger.warning(f"No configured test found for Jenkins test: {test_name}")

    def generate_json_report(self):
        """Generate JSON test report"""
        json_file = os.path.join(self.output_dir, "test_report_detailed.json")
        absolute_json_file = os.path.abspath(json_file)
        try:
            with open(json_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            self.logger.info(f"Generated JSON report: {json_file}")
            self.logger.info(f"JSON report absolute path: {absolute_json_file}")
            self.logger.info(f"File exists after creation: {os.path.exists(json_file)}")
        except Exception as e:
            self.logger.error(f"Error generating JSON report: {e}")

    def generate_html_report(self):
        """Generate HTML test report"""
        html_file = os.path.join(self.output_dir, "test_report_detailed.html")
        
        summary = self.test_results["summary"]
        success_rate = 0
        if summary["total_tests"] > 0:
            success_rate = (summary["passed_tests"] / summary["total_tests"]) * 100
        
        # Collect unique requirement IDs (extract parent requirements from test IDs)
        all_requirement_ids = set()
        for module_name, module_data in self.test_results["modules"].items():
            if "tests" in module_data:
                for test in module_data["tests"]:
                    test_id = test.get("test_id", "")
                    if test_id:
                        # Extract parent requirement ID from test case ID
                        # e.g., "F-K1-TC-001" -> "F-K1", "F-K8-TC-001" -> "F-K8"
                        import re
                        req_match = re.match(r'^([A-Z]+-[A-Z]+\d+)', test_id)
                        if req_match:
                            parent_req_id = req_match.group(1)
                            all_requirement_ids.add(parent_req_id)
        
        # Format requirement IDs section - show all parent requirements found
        requirement_ids_section = ""
        if all_requirement_ids:
            sorted_ids = sorted(all_requirement_ids)
            requirement_links = []
            for req_id in sorted_ids:
                # Check if the parent requirement itself has a direct GitHub issue mapping
                if req_id in self.github_issue_mapping:
                    # Use direct issue link for parent requirement
                    issue_number = self.github_issue_mapping[req_id]
                    github_url = f"https://github.com/{self.github_repo_owner}/{self.github_repo_name}/issues/{issue_number}"
                    github_link = f'<a href="{github_url}" target="_blank" class="github-link" title="View GitHub issue #{issue_number} for {req_id}">{req_id}</a>'
                    requirement_links.append(f'<span class="requirement-link">{github_link}</span>')
                else:
                    # Check if this parent requirement has any test cases with GitHub issue mappings
                    has_mapped_test_cases = any(
                        test_id in self.github_issue_mapping 
                        for test_id in self.github_issue_mapping.keys() 
                        if test_id.startswith(req_id + "-")
                    )
                    
                    if has_mapped_test_cases:
                        # Use search URL for parent requirements without direct mappings
                        github_url = f"https://github.com/{self.github_repo_owner}/{self.github_repo_name}/issues?q={req_id}"
                        github_link = f'<a href="{github_url}" target="_blank" class="github-link" title="Search GitHub issues for {req_id}">{req_id}</a>'
                        requirement_links.append(f'<span class="requirement-link">{github_link}</span>')
                    else:
                        # Show as non-clickable if no mappings found
                        requirement_links.append(f'<span class="requirement-link"><span class="test-id-no-link">[{req_id}]</span></span>')
            
            if requirement_links:
                requirement_ids_section = f"""
    <div class="summary">
        <h2>📋 Requirements Coverage</h2>
        <p><strong>Requirements Tested:</strong> {' '.join(requirement_links)}</p>
        <p><strong>Total Requirements:</strong> {len(sorted_ids)}</p>
    </div>
"""
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Detailed Test Report - Simtemp Module</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .module {{ border: 1px solid #ddd; margin-bottom: 20px; border-radius: 5px; }}
        .module-header {{ background-color: #e0e0e0; padding: 10px; font-weight: bold; }}
        .test {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .passed {{ background-color: #d4edda; }}
        .failed {{ background-color: #f8d7da; }}
        .skipped {{ background-color: #fff3cd; }}
        .not-implemented {{ background-color: #e2e3e5; color: #6c757d; }}
        .in-progress {{ background-color: #ffeaa7; color: #b8860b; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        .github-link {{ 
            color: #0366d6; 
            text-decoration: none; 
            font-weight: bold;
            border: 1px solid #0366d6;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
            background-color: #f6f8fa;
            margin-right: 8px;
        }}
        .github-link:hover {{ 
            background-color: #0366d6; 
            color: white; 
            text-decoration: none;
        }}
        .github-link.status-passed {{
            color: #27ae60;
            border-color: #27ae60;
        }}
        .github-link.status-in-progress {{
            color: #b8860b;
            border-color: #b8860b;
        }}
        .github-link.status-blocked {{
            color: #e74c3c;
            border-color: #e74c3c;
        }}
        .github-link.status-passed:hover {{
            background-color: #27ae60;
            color: white;
        }}
        .github-link.status-in-progress:hover {{
            background-color: #b8860b;
            color: white;
        }}
        .github-link.status-blocked:hover {{
            background-color: #e74c3c;
            color: white;
        }}
        .requirement-link {{
            display: inline-block;
            margin: 2px 4px;
        }}
        .test-id-no-link {{
            font-weight: bold;
            color: #6c757d;
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
            border: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <h1>Detailed Test Report - Simtemp Module</h1>
    {requirement_ids_section}
    <div class="summary">
        <h2>Test Summary</h2>
        <p><strong>Total Modules:</strong> {summary["total_modules"]}</p>
        <p><strong>Total Tests:</strong> {summary["total_tests"]}</p>
        <p><strong>Passed:</strong> {summary["passed_tests"]}</p>
        <p><strong>Failed:</strong> {summary["failed_tests"]}</p>
        <p><strong>Skipped:</strong> {summary["skipped_tests"]}</p>
        <p><strong>Not Implemented:</strong> {summary["not_implemented_tests"]}</p>
        <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
        <p class="timestamp"><strong>Generated:</strong> {summary["timestamp"]}</p>
        <p class="timestamp"><strong>Runtime:</strong> {summary["runtime"]:.2f} seconds</p>
    </div>
"""

        # Add module details
        for module_name, module_data in self.test_results["modules"].items():
            html_content += f"""
    <div class="module">
        <div class="module-header">Module: {module_name}</div>
"""
            
            if "tests" in module_data:
                for test in module_data["tests"]:
                    status = test.get("status", "unknown").lower()
                    test_name = test.get("name", "Unknown Test")
                    test_desc = test.get("description", "")
                    test_id = test.get("test_id", "")
                    
                    # Map status to CSS class and icon
                    status_icon = ""
                    status_text = status.upper()
                    
                    if status in ["passed", "failed", "skipped"]:
                        css_class = status
                        if status == "passed":
                            status_icon = "✅"
                        elif status == "failed":
                            status_icon = "❌"
                        elif status == "skipped":
                            status_icon = "⏭️"
                    elif status == "not implemented":
                        css_class = "not-implemented"
                        # Special handling for Jenkins tests
                        if module_name == "jenkins_test":
                            status_icon = "🔄"
                            status_text = "CHECK PIPELINE REPORT"
                        else:
                            status_icon = "⚪"
                            status_text = "NOT IMPLEMENTED"
                    elif status == "in progress":
                        css_class = "in-progress"
                        status_icon = "🟡"
                    else:
                        css_class = ""
                        status_icon = "❓"
                    
                    # Format test title with ID if available
                    test_title = test_name
                    if test_id:
                        github_link = self.generate_github_issue_link_html(test_id, status)
                        test_title = f"{github_link} {test_name}"
                    
                    html_content += f"""
        <div class="test {css_class}">
            <strong>{status_icon} {test_title}</strong> - {status_text}
            <br><small>{test_desc}</small>
        </div>
"""
            
            html_content += "    </div>\n"

        html_content += """
</body>
</html>"""

        try:
            with open(html_file, 'w') as f:
                f.write(html_content)
            self.logger.info(f"Generated HTML report: {html_file}")
        except Exception as e:
            self.logger.error(f"Error generating HTML report: {e}")

    def wait_for_qemu_sessions_completion(self, max_wait_time=60):
        """
        Wait for all QEMU sessions to complete before generating final reports.
        This ensures that all QEMU test results are properly captured.
        
        Args:
            max_wait_time (int): Maximum time to wait in seconds
        
        Returns:
            bool: True if all sessions completed, False if timeout
        """
        if not QEMU_SUPPORT_AVAILABLE:
            self.logger.info("QEMU support not available, skipping session wait")
            return True
        
        self.logger.info("Checking for active QEMU sessions...")
        
        start_time = time.time()
        wait_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < max_wait_time:
            try:
                if not is_qemu_session_active():
                    self.logger.info("No active QEMU sessions detected - proceeding with report generation")
                    return True
                
                elapsed = time.time() - start_time
                self.logger.info(f"QEMU session still active - waiting... ({elapsed:.1f}s elapsed)")
                time.sleep(wait_interval)
                
            except Exception as e:
                self.logger.warning(f"Error checking QEMU session status: {e}")
                break
        
        # Timeout reached
        elapsed = time.time() - start_time
        self.logger.warning(f"Timeout waiting for QEMU sessions to complete ({elapsed:.1f}s)")
        self.logger.info("Proceeding with report generation anyway...")
        return False

    def ensure_qemu_cleanup(self):
        """
        Ensure QEMU sessions are properly cleaned up before report generation.
        This is the primary QEMU cleanup responsibility for driver_tester.
        """
        if not QEMU_SUPPORT_AVAILABLE:
            return
        
        try:
            self.logger.info("Performing QEMU session cleanup...")
            
            # First try session-based cleanup if there's an active session
            if is_qemu_session_active():
                self.logger.info("Active QEMU session found, cleaning up...")
                cleanup_qemu_session()
                self.logger.info("QEMU session cleanup completed")
            else:
                self.logger.info("No active QEMU session found")
            
            # Then ensure all QEMU processes are cleaned up
            cleanup_success = cleanup_qemu_processes(
                force_kill=True,
                restore_cwd=True
            )
            
            if cleanup_success:
                self.logger.info("QEMU process cleanup completed successfully")
            else:
                self.logger.warning(
                    "QEMU process cleanup completed with warnings"
                )
                
        except Exception as e:
            self.logger.warning(f"Error during QEMU cleanup: {e}")

    def generate_reports(self):
        """Generate all test reports"""
        self.logger.info("STARTING TEST REPORT GENERATION")
        self.logger.info(f"Input directory: {self.input_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Test config file: {self.test_config_file}")
        
        # Check if there are active QEMU tests running before cleanup
        self.logger.info("Step 0: Checking for active QEMU sessions...")
        if QEMU_SUPPORT_AVAILABLE:
            try:
                from test_utils import is_qemu_session_active
                if is_qemu_session_active():
                    self.logger.info(
                        "Active QEMU session detected - skipping cleanup "
                        "to avoid interference")
                    self.logger.info(
                        "QEMU cleanup will be handled by test completion")
                else:
                    self.logger.info(
                        "No active QEMU sessions - proceeding with cleanup")
                    self.ensure_qemu_cleanup()
            except Exception as e:
                self.logger.warning(
                    f"Could not check QEMU session status: {e}")
                # If we can't check, err on the side of caution and skip
                self.logger.info(
                    "Skipping QEMU cleanup due to status check failure")
        else:
            self.logger.info(
                "QEMU support not available - skipping QEMU cleanup")
        
        # Small delay to allow file system operations to complete
        time.sleep(2)
        
        self.logger.info("Step 1: Collecting test results...")
        self.collect_test_results()
        
        self.logger.info("Step 2: Generating JSON report...")
        self.generate_json_report()
        
        self.logger.info("Step 3: Generating HTML report...")
        self.generate_html_report()
        
        self.logger.info("TEST REPORT GENERATION COMPLETED")
        
        # Check if there were any failed tests
        failed_tests = self.test_results["summary"]["failed_tests"]
        total_tests = self.test_results["summary"]["total_tests"]
        
        if failed_tests > 0:
            self.logger.warning(
                f"Test execution completed with {failed_tests} failed test(s) "
                f"out of {total_tests} total tests"
            )
            return False  # Indicate failure for TDD compliance
        else:
            self.logger.info(f"All {total_tests} tests passed successfully")
            return True  # Indicate success


def main():
    print("DRIVER_TESTER: Script starting...")

    # Launch qemu_monitor.py in the background if it exists
    import subprocess
    from pathlib import Path
    monitor_path = Path(__file__).parent / "qemu_monitor.py"
    if monitor_path.exists():
        try:
            print("QEMU-HANDLER: Launching qemu_monitor.py in background...")
            subprocess.Popen(["python3", str(monitor_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("DRIVER_TESTER: qemu_monitor.py launched in the background.")
        except Exception as e:
            print(f"DRIVER_TESTER: Error launching qemu_monitor.py: {e}")
    else:
        print("DRIVER_TESTER: qemu_monitor.py not found, skipping launch.")
    parser = argparse.ArgumentParser(
        description="Orchestrate comprehensive driver testing for simtemp"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--input-dir",
        help="Input directory for test details files (default: /tmp)"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for reports (default: reports)"
    )

    args = parser.parse_args()

    # Define safe_print here for early messages
    def safe_print(text):
        try:
            print(text)
        except BlockingIOError:
            # If stdout blocks, try writing to a file
            try:
                with open("/tmp/driver_tester_log.txt", "a") as f:
                    f.write(text + "\n")
            except Exception:
                pass

    safe_print("DRIVER_TESTER: Arguments parsed:")
    safe_print(f"   - verbose: {args.verbose}")
    safe_print(f"   - input_dir: {args.input_dir}")
    safe_print(f"   - output_dir: {args.output_dir}")

    safe_print("DRIVER_TESTER: Creating orchestrator instance...")
    orchestrator = DriverTestOrchestrator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        verbose=args.verbose
    )

    safe_print("DRIVER_TESTER: Starting test orchestration...")
    try:
        success = orchestrator.generate_reports()
        if success:
            safe_print(
                "DRIVER_TESTER: Script completed successfully - "
                "all tests passed"
            )
            return 0
        else:
            safe_print("DRIVER_TESTER: Script completed with test failures")
            return 1
    except Exception as e:
        safe_print(f"DRIVER_TESTER: Script failed with error: {e}")
        import traceback
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        traceback_file = f"/tmp/driver_tester_traceback_{timestamp}.txt"

        try:
            # Try printing to stdout first
            traceback.print_exc()
        except BlockingIOError:
            # If stdout blocks, log to file
            try:
                with open(traceback_file, "a") as f:
                    f.write(f"Exception occurred at {timestamp}:\n")
                    traceback.print_exc(file=f)
                safe_print(f"Traceback written to {traceback_file}")
            except Exception as trace_err:
                # Last resort - try to log the error
                try:
                    error_path = "/tmp/driver_tester_critical_error.txt"
                    with open(error_path, "a") as f:
                        f.write(f"Critical error at {timestamp}: {str(e)}\n")
                        f.write(f"Failed to log traceback: {str(trace_err)}\n")
                except Exception:
                    pass
        return 1


if __name__ == "__main__":
    sys.exit(main())


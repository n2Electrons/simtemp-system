#!/usr/bin/env python3
"""
create_detailed_test_report.py - Generate a detailed test report for simtemp modules

Copyright (c) Jorge Rodriguez Moreno

This script:
1. Reads test configuration from simtemp_tests.yml
2. Collects test details from test_details_{module}.json files and pytest results
3. Combines them into a single structured report
4. Generates an HTML and JSON report with comprehensive test results

Usage: ./create_detailed_test_report.py [--verbose] [--input-dir /path] [--output-dir /path]
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


class TestLogger:
    def __init__(self, verbose=False):
        self.verbose = verbose
    
    def info(self, message):
        print(f"[INFO] {message}")
    
    def debug(self, message):
        if self.verbose:
            print(f"[DEBUG] {message}")
    
    def warning(self, message):
        print(f"[WARNING] {message}")
    
    def error(self, message):
        print(f"[ERROR] {message}")


class DetailedTestReportGenerator:
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
        self.github_repo_name = os.getenv("GITHUB_REPO", "challenge_2509")
        
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
                self.logger.warning("No GitHub token found in environment variable 'GITHUB_TOKEN'. Requests will be unauthenticated and may be rate-limited.")
            
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
        """Collect test results from test configuration and any available test detail files"""
        start_time = time.time()
        
        # First, collect results from test_details_*.json files if they exist
        detail_files = self.find_test_detail_files()
        for file_path in detail_files:
            module_name = self.extract_module_name(file_path)
            test_details = self.load_test_details(file_path)
            
            if test_details:
                self.test_results["modules"][module_name] = test_details
                self.test_results["summary"]["total_modules"] += 1
                
                if "tests" in test_details:
                    for test in test_details["tests"]:
                        self.test_results["summary"]["total_tests"] += 1
                        status = test.get("status", "unknown").lower()
                        if status == "passed":
                            self.test_results["summary"]["passed_tests"] += 1
                        elif status == "failed":
                            self.test_results["summary"]["failed_tests"] += 1
                        elif status == "skipped":
                            self.test_results["summary"]["skipped_tests"] += 1
        
        # If no detail files found, generate results from test configuration
        if self.test_results["summary"]["total_modules"] == 0:
            self.logger.info("No test detail files found, generating from test configuration")
            self.generate_from_config()
        
        self.test_results["summary"]["runtime"] = time.time() - start_time
        self.logger.info(f"Collected results from {self.test_results['summary']['total_modules']} modules")

    def generate_from_config(self):
        """Generate test results structure from test configuration"""
        if not self.test_config or 'tests' not in self.test_config:
            self.logger.error("No test configuration available")
            return
            
        for test_suite_name, test_suite_config in self.test_config['tests'].items():
            if not test_suite_config.get('enabled', True):
                continue
                
            module_data = {
                "name": test_suite_name,
                "description": test_suite_config.get('description', ''),
                "enabled": True,
                "tests": []
            }
            
            # Add test cases from configuration
            test_cases = test_suite_config.get('test_cases', [])
            for test_case in test_cases:
                if test_case.get('enabled', True):
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
        self.capture_pytest_results(module_data)
        
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

    def capture_pytest_results(self, module_data):
        """Run pytest and capture results to update test status"""
        try:
            import subprocess
            
            # Run pytest with JSON output
            self.logger.info("Running pytest to capture actual test results...")
            
            # Find test files in the script directory
            script_dir = Path(__file__).parent
            test_files = list(script_dir.glob("test_*.py"))
            
            if not test_files:
                self.logger.warning("No test files found")
                return
                
            # Convert to string paths
            test_file_paths = [str(f) for f in test_files]
            
            # Run pytest with verbose output from the correct directory
            cmd = ["python3", "-m", "pytest", "-v", "--tb=short"] + test_file_paths
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=script_dir)
            
            # Parse pytest output
            self.parse_pytest_output(result.stdout, module_data)
            
        except Exception as e:
            self.logger.error(f"Error running pytest: {e}")

    def parse_pytest_output(self, pytest_output, module_data):
        """Parse pytest output to extract test results"""
        lines = pytest_output.split('\n')
        
        for line in lines:
            # Look for test result lines like: "test_kernel_driver.py::test_insmod_registers_driver PASSED"
            if '::test_' in line and (' PASSED' in line or ' FAILED' in line or ' SKIPPED' in line):
                parts = line.split('::')
                if len(parts) >= 2:
                    test_file = parts[0].strip()
                    test_info = parts[1].strip()
                    
                    # Extract test name and status
                    if ' PASSED' in test_info:
                        test_name = test_info.replace(' PASSED', '').strip()
                        status = 'passed'
                    elif ' FAILED' in test_info:
                        test_name = test_info.replace(' FAILED', '').strip()
                        status = 'failed'
                    elif ' SKIPPED' in test_info:
                        test_name = test_info.replace(' SKIPPED', '').strip()
                        status = 'skipped'
                    else:
                        continue
                    
                    # Update matching test in module_data
                    self.update_test_status(module_data, test_name, status)
                    
        # Also look for summary line like "1 passed in 4.85s"
        for line in lines:
            if ' passed in ' in line or ' failed' in line:
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
                test['message'] = f"Test executed via pytest"
                
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
                "description": f"Actual pytest test: {test_name}",
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

    def generate_json_report(self):
        """Generate JSON test report"""
        json_file = os.path.join(self.output_dir, "test_report_detailed.json")
        try:
            with open(json_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            self.logger.info(f"Generated JSON report: {json_file}")
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
                        status_icon = "⚪"
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
            <strong>{status_icon} {test_title}</strong> - {status.upper()}
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

    def generate_reports(self):
        """Generate all test reports"""
        self.collect_test_results()
        self.generate_json_report()
        self.generate_html_report()
        
        self.logger.info("Test report generation completed")


def main():
    parser = argparse.ArgumentParser(description="Generate detailed test reports for simtemp modules")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--input-dir", help="Input directory for test details files (default: /tmp)")
    parser.add_argument("--output-dir", help="Output directory for reports (default: reports)")
    
    args = parser.parse_args()
    
    generator = DetailedTestReportGenerator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        verbose=args.verbose
    )
    
    try:
        generator.generate_reports()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
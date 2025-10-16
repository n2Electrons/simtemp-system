#!/usr/bin/env python3
"""
Jenkins QEMU Integration Handler
Processes simtemp_tests.yml to determine QEMU execution requirements
and handles results collection for Jenkins reporting.

Copyright (c) Jorge Rodriguez Moreno
"""

import os
import sys
import yaml
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional


class JenkinsQemuIntegration:
    """Handler for QEMU tests in Jenkins environment"""
    
    def __init__(self, config_path: str = None):
        self.workspace_root = os.environ.get('WORKSPACE', os.getcwd())
        self.config_path = config_path or 'simtemp/tests/config/simtemp_tests.yml'
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load test configuration from YAML file"""
        config_file = os.path.join(self.workspace_root, self.config_path)
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def get_qemu_test_suites(self) -> Dict[str, Dict]:
        """Get all test suites configured for QEMU execution"""
        qemu_suites = {}
        tests = self.config.get('tests', {})
        
        for suite_name, suite_config in tests.items():
            execution_env = suite_config.get('execution_environment', {})
            if execution_env.get('type') == 'qemu':
                qemu_suites[suite_name] = suite_config
                
        return qemu_suites
    
    def is_qemu_test_suite(self, suite_name: str) -> bool:
        """Check if a test suite is configured for QEMU execution"""
        tests = self.config.get('tests', {})
        suite_config = tests.get(suite_name, {})
        execution_env = suite_config.get('execution_environment', {})
        return execution_env.get('type') == 'qemu'
    
    def get_qemu_execution_command(self, suite_name: str) -> Optional[str]:
        """Generate QEMU execution command for a test suite"""
        if not self.is_qemu_test_suite(suite_name):
            return None
            
        suite_config = self.config['tests'][suite_name]
        qemu_config = suite_config.get('qemu_config', {})
        
        runner_script = qemu_config.get('runner_script')
        if not runner_script:
            raise ValueError(f"No runner_script defined for QEMU suite: {suite_name}")
            
        runner_path = os.path.join(self.workspace_root, runner_script)
        if not os.path.exists(runner_path):
            raise FileNotFoundError(f"QEMU runner script not found: {runner_path}")
            
        return f"bash {runner_path}"
    
    def get_results_collection_config(self, suite_name: str) -> Dict:
        """Get results collection configuration for a QEMU test suite"""
        if not self.is_qemu_test_suite(suite_name):
            return {}
            
        suite_config = self.config['tests'][suite_name]
        return suite_config.get('results_collection', {})
    
    def setup_results_directory(self, suite_name: str) -> str:
        """Setup and return results directory path"""
        results_config = self.get_results_collection_config(suite_name)
        results_base = results_config.get('results_base_path', 'simtemp/tests/results')
        results_dir = os.path.join(self.workspace_root, results_base)
        
        os.makedirs(results_dir, exist_ok=True)
        return results_dir
    
    def execute_qemu_test_suite(self, suite_name: str) -> Dict:
        """Execute a QEMU test suite and return execution results"""
        print(f"🚀 Executing QEMU test suite: {suite_name}")
        
        # Setup results directory
        results_dir = self.setup_results_directory(suite_name)
        print(f"📁 Results directory: {results_dir}")
        
        # Get execution command
        command = self.get_qemu_execution_command(suite_name)
        if not command:
            raise ValueError(f"Cannot generate execution command for suite: {suite_name}")
        
        print(f"🏃 Running command: {command}")
        
        # Get timeout from configuration
        suite_config = self.config['tests'][suite_name]
        execution_env = suite_config.get('execution_environment', {})
        timeout_minutes = execution_env.get('timeout_minutes', 10)
        timeout_seconds = timeout_minutes * 60
        
        # Execute QEMU test
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                timeout=timeout_seconds,
                capture_output=True,
                text=True
            )
            execution_time = time.time() - start_time
            
            execution_result = {
                'suite_name': suite_name,
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': execution_time,
                'timeout_seconds': timeout_seconds,
                'success': result.returncode == 0
            }
            
        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time
            execution_result = {
                'suite_name': suite_name,
                'command': command,
                'returncode': -1,
                'stdout': e.stdout or '',
                'stderr': e.stderr or '',
                'execution_time': execution_time,
                'timeout_seconds': timeout_seconds,
                'success': False,
                'error': 'Test execution timed out'
            }
        
        print(f"⏱️  Execution completed in {execution_result['execution_time']:.2f} seconds")
        print(f"✅ Success: {execution_result['success']}")
        
        return execution_result
    
    def collect_test_results(self, suite_name: str) -> Dict:
        """Collect test results from QEMU execution"""
        results_config = self.get_results_collection_config(suite_name)
        results_base = results_config.get('results_base_path', 'simtemp/tests/results')
        results_dir = os.path.join(self.workspace_root, results_base)
        
        patterns = results_config.get('patterns', {})
        collected_results = {
            'suite_name': suite_name,
            'results_directory': results_dir,
            'files': {}
        }
        
        # Collect files by pattern
        for result_type, pattern in patterns.items():
            matching_files = []
            if os.path.exists(results_dir):
                for file in os.listdir(results_dir):
                    if self._matches_pattern(file, pattern):
                        file_path = os.path.join(results_dir, file)
                        matching_files.append({
                            'name': file,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'exists': True
                        })
            
            collected_results['files'][result_type] = matching_files
        
        # Summary
        total_files = sum(len(files) for files in collected_results['files'].values())
        collected_results['summary'] = {
            'total_files_collected': total_files,
            'collection_successful': total_files > 0
        }
        
        return collected_results
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching for file collection"""
        # Convert simple glob patterns to basic matching
        if '*' in pattern:
            # Simple wildcard matching
            pattern_parts = pattern.split('*')
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                return filename.startswith(prefix) and filename.endswith(suffix)
        return filename == pattern
    
    def generate_jenkins_artifacts_info(self, suite_name: str) -> Dict:
        """Generate Jenkins artifacts information for a QEMU test suite"""
        results_config = self.get_results_collection_config(suite_name)
        patterns = results_config.get('patterns', {})
        
        jenkins_info = {
            'suite_name': suite_name,
            'execution_type': 'qemu',
            'artifacts': {
                'junit_xml': {
                    'pattern': patterns.get('junit_xml', '*-results.xml'),
                    'publish_pattern': f"{results_config.get('results_base_path', 'simtemp/tests/results')}/*-results.xml",
                    'publisher': 'publishTestResults'
                },
                'json_reports': {
                    'pattern': patterns.get('json_report', '*-report.json'),
                    'archive_pattern': f"{results_config.get('results_base_path', 'simtemp/tests/results')}/*-report.json",
                    'publisher': 'archiveArtifacts'
                },
                'console_logs': {
                    'pattern': patterns.get('console_log', '*-console.log'),
                    'archive_pattern': f"{results_config.get('results_base_path', 'simtemp/tests/results')}/*-console.log",
                    'publisher': 'archiveArtifacts'
                },
                'all_artifacts': {
                    'pattern': patterns.get('artifacts', 'test-results/*'),
                    'archive_pattern': patterns.get('artifacts', 'test-results/*'),
                    'publisher': 'archiveArtifacts'
                }
            }
        }
        
        return jenkins_info


def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python3 jenkins_qemu_integration.py <command> [suite_name]")
        print("Commands:")
        print("  list_qemu_suites    - List all QEMU test suites")
        print("  execute <suite>     - Execute a QEMU test suite")
        print("  collect <suite>     - Collect results from a QEMU test suite")
        print("  jenkins_info <suite> - Get Jenkins artifacts info for a suite")
        return 1
    
    command = sys.argv[1]
    integration = JenkinsQemuIntegration()
    
    if command == "list_qemu_suites":
        qemu_suites = integration.get_qemu_test_suites()
        print(f"Found {len(qemu_suites)} QEMU test suites:")
        for suite_name, config in qemu_suites.items():
            print(f"  - {suite_name}: {config.get('description', 'No description')}")
    
    elif command == "execute":
        if len(sys.argv) < 3:
            print("Error: suite_name required for execute command")
            return 1
        
        suite_name = sys.argv[2]
        try:
            result = integration.execute_qemu_test_suite(suite_name)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error executing suite {suite_name}: {e}")
            return 1
    
    elif command == "collect":
        if len(sys.argv) < 3:
            print("Error: suite_name required for collect command")
            return 1
        
        suite_name = sys.argv[2]
        try:
            results = integration.collect_test_results(suite_name)
            print(json.dumps(results, indent=2))
        except Exception as e:
            print(f"Error collecting results for suite {suite_name}: {e}")
            return 1
    
    elif command == "jenkins_info":
        if len(sys.argv) < 3:
            print("Error: suite_name required for jenkins_info command")
            return 1
        
        suite_name = sys.argv[2]
        try:
            info = integration.generate_jenkins_artifacts_info(suite_name)
            print(json.dumps(info, indent=2))
        except Exception as e:
            print(f"Error generating Jenkins info for suite {suite_name}: {e}")
            return 1
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
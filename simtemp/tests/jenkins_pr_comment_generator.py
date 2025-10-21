#!/usr/bin/env python3
"""
Jenkins PR Comment Generator with Markdown Table Format for Python Test Files

This script integrates with the existing Jenkins pipeline to generate PR comments
that display all Python test files and their results in a clean Markdown table.
"""

import os
import json
import yaml
import glob
import subprocess
from datetime import datetime

def load_pipeline_config():
    """Load pipeline configuration"""
    config_path = os.environ.get('ACTUAL_PIPELINE_CONFIG_PATH', 'simtemp/pipeline_config.yml')
    
    # Try alternative paths if the default doesn't exist
    alternative_paths = [
        config_path,
        'simtemp/pipeline_config.yml',
        'pipeline_config.yml'
    ]
    
    for path in alternative_paths:
        if os.path.exists(path):
            print(f"Loading pipeline config from: {path}")
            try:
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load {path}: {e}")
                continue
    
    print(f"Warning: No pipeline config found in any of: {alternative_paths}")
    return {}

def load_test_config():
    """Load test configuration from environment or default path"""
    test_config_path = os.environ.get('TEST_CONFIG_PATH', 'simtemp/tests/config/simtemp_tests.yml')
    
    # Try alternative paths if the default doesn't exist
    alternative_paths = [
        test_config_path,
        'simtemp/tests/config/simtemp_tests.yml',
        'tests/config/simtemp_tests.yml',
        'config/simtemp_tests.yml'
    ]
    
    for path in alternative_paths:
        if os.path.exists(path):
            print(f"Loading test config from: {path}")
            try:
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load {path}: {e}")
                continue
    
    print(f"Warning: No test config found in any of: {alternative_paths}")
    return {}

def load_detailed_test_report():
    """Load detailed test report JSON if available"""
    # Try common report locations
    report_paths = [
        "simtemp/tests/reports/test_report_detailed.json",
        "reports/test_report_detailed.json",
        "/tmp/test_report_detailed.json"
    ]
    
    for report_path in report_paths:
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load {report_path}: {e}")
    
    return None

def extract_python_files_from_config(test_config):
    """Extract all Python test files from test configuration"""
    python_files = {}
    
    if not test_config.get('tests'):
        return python_files
    
    for suite_name, suite_config in test_config['tests'].items():
        if not suite_config.get('enabled', True):
            continue
            
        test_cases = suite_config.get('test_cases', [])
        for test_case in test_cases:
            # Only include enabled test cases
            if not test_case.get('enabled', True):
                continue
                
            pytest_file = test_case.get('pytest_file')
            test_id = test_case.get('test_id', 'N/A')
            
            if pytest_file and pytest_file.endswith('.py'):
                # Use a unique key combining test_id and pytest_file to handle duplicates
                unique_key = f"{test_id}#{pytest_file}"
                
                python_files[unique_key] = {
                    'pytest_file': pytest_file,
                    'test_id': test_id,
                    'test_name': test_case.get('name', ''),
                    'description': test_case.get('description', ''),
                    'suite': suite_name,
                    'enabled': test_case.get('enabled', True)
                }
    
    return python_files


def extract_disabled_test_files(test_config):
    """Extract disabled test files for counting purposes"""
    disabled_files = {}
    
    if not test_config.get('tests'):
        return disabled_files
    
    for suite_name, suite_config in test_config['tests'].items():
        if not suite_config.get('enabled', True):
            continue
            
        test_cases = suite_config.get('test_cases', [])
        for test_case in test_cases:
            # Only include disabled test cases
            if test_case.get('enabled', True):
                continue
                
            pytest_file = test_case.get('pytest_file')
            test_id = test_case.get('test_id', 'N/A')
            
            if pytest_file and pytest_file.endswith('.py'):
                unique_key = f"{test_id}#{pytest_file}"
                disabled_files[unique_key] = {
                    'pytest_file': pytest_file,
                    'test_id': test_id,
                    'suite': suite_name
                }
    
    return disabled_files


def get_test_status_from_report(pytest_file, test_id, detailed_report):
    """Get test status for a specific Python file and test ID from detailed report"""
    if not detailed_report or not detailed_report.get('modules'):
        return None

    # Search through all modules in the report
    for module_name, module_data in detailed_report['modules'].items():
        if module_data.get('tests'):
            for test in module_data['tests']:
                # Match by test_id first (most reliable)
                report_test_id = test.get('test_id', '')
                if report_test_id == test_id:
                    return test.get('status', 'unknown')
                
                # Fallback: match by pytest_file if test_id doesn't match
                test_pytest_file = test.get('pytest_file', '')
                if test_pytest_file == pytest_file:
                    return test.get('status', 'unknown')

    return None

def generate_build_status_section():
    """Generate build status section"""
    build_number = os.environ.get('BUILD_NUMBER', 'unknown')
    build_url = os.environ.get('BUILD_URL', '')
    job_name = os.environ.get('JOB_NAME', 'unknown')
    branch_name = os.environ.get('BRANCH_NAME', 'unknown')
    
    lines = []
    lines.append("## 🧪 Test Results with Python Files")
    lines.append(f"**Branch:** `{branch_name}` | **Build:** [#{build_number}]({build_url}) | **Job:** {job_name}")
    lines.append("")
    
    return lines

def generate_python_files_table(test_config, detailed_report=None):
    """Generate Markdown table with all Python test files organized by test suite"""
    python_files = extract_python_files_from_config(test_config)
    
    if not python_files:
        return ["⚠️ No Python test files found in configuration."]
    
    lines = []
    
    # Group files by test suite
    suites = {}
    for unique_key, info in python_files.items():
        suite_name = info['suite']
        if suite_name not in suites:
            suites[suite_name] = []
        suites[suite_name].append((unique_key, info))
    
    # Sort suites by name for consistent ordering
    sorted_suites = sorted(suites.items())
    
    for suite_name, suite_files in sorted_suites:
        # Add suite header
        lines.append(f"### 📋 {suite_name}")
        lines.append("")
        
        # Add table header for this suite
        lines.append("| Status | Test ID | Python File | Test Name | Description |")
        lines.append("|--------|---------|-------------|-----------|-------------|")
        
        # Sort files within suite by test ID
        sorted_files = sorted(suite_files, key=lambda x: x[1]['test_id'])
        
        for unique_key, info in sorted_files:
            pytest_file = info['pytest_file']
            
            # Determine status icon
            status_icon = "🔵"  # Default for configured
            
            if not info['enabled']:
                status_icon = "⚪"  # Disabled
            elif detailed_report:
                test_status = get_test_status_from_report(pytest_file, info['test_id'], detailed_report)
                if test_status:
                    status_map = {
                        'passed': '✅',
                        'failed': '❌',
                        'skipped': '⏭️',
                        'not implemented': '⚪',
                        'error': '❌'
                    }
                    status_icon = status_map.get(test_status.lower(), '🔵')
            
            test_id = info['test_id']
            test_name = info['test_name'] or 'N/A'
            description = info['description'] or 'N/A'
            
            # Format table row
            lines.append(f"| {status_icon} | `{test_id}` | `{pytest_file}` | {test_name} | {description} |")
        
        lines.append("")  # Add space between suites
    
    return lines

def generate_summary_section(test_config, detailed_report=None):
    """Generate summary section with suite breakdown"""
    python_files = extract_python_files_from_config(test_config)
    
    # Also get counts of disabled tests for informational purposes
    disabled_files = extract_disabled_test_files(test_config)
    
    lines = []
    lines.append("### 📊 Summary")
    
    # Overall summary (only showing enabled tests)
    lines.append(f"- **Enabled test files displayed:** {len(python_files)}")
    
    if disabled_files:
        lines.append(f"- **Disabled tests (not shown):** {len(disabled_files)}")
    
    # Suite breakdown (only enabled tests)
    if python_files:
        lines.append("")
        lines.append("**Enabled Tests by Suite:**")
        
        # Group by suite for summary
        suite_counts = {}
        for info in python_files.values():
            suite_name = info['suite']
            if suite_name not in suite_counts:
                suite_counts[suite_name] = 0
            suite_counts[suite_name] += 1
        
        for suite_name, count in sorted(suite_counts.items()):
            lines.append(f"- **{suite_name}:** {count} enabled")
    
    # Add test execution summary if we have detailed report
    if detailed_report and detailed_report.get('summary'):
        summary = detailed_report['summary']
        total_tests = summary.get('total_tests', 0)
        passed_tests = summary.get('passed_tests', 0)
        failed_tests = summary.get('failed_tests', 0)
        
        if total_tests > 0:
            lines.append("")
            lines.append("**Test Execution Results:**")
            lines.append(f"- **Total tests executed:** {total_tests}")
            lines.append(f"- **Passed:** {passed_tests}")
            lines.append(f"- **Failed:** {failed_tests}")
            
            success_rate = (passed_tests * 100 // total_tests) if total_tests > 0 else 0
            lines.append(f"- **Success rate:** {success_rate}%")
    
    return lines

def generate_legend_section():
    """Generate legend section"""
    lines = []
    lines.append("### 📝 Legend")
    lines.append("- ✅ **Passed** - Test executed successfully")
    lines.append("- ❌ **Failed** - Test execution failed")
    lines.append("- ⏭️ **Skipped** - Test was skipped")
    lines.append("- ⚪ **Not Implemented/Disabled** - Test not yet implemented or disabled")
    lines.append("- 🔵 **Configured** - Test configured but no execution results")
    
    return lines

def generate_pr_comment_with_table():
    """Generate complete PR comment with Python files in table format"""
    # Load configurations
    test_config = load_test_config()
    detailed_report = load_detailed_test_report()
    
    # Build comment sections
    comment_lines = []
    
    # Build status section
    comment_lines.extend(generate_build_status_section())
    
    # Python files table
    comment_lines.extend(generate_python_files_table(test_config, detailed_report))
    comment_lines.append("")
    
    # Summary section
    comment_lines.extend(generate_summary_section(test_config, detailed_report))
    comment_lines.append("")
    
    # Legend section
    comment_lines.extend(generate_legend_section())
    comment_lines.append("")
    
    # Footer
    comment_lines.append("---")
    comment_lines.append("*Generated automatically by Jenkins CI with Python test file mapping*")
    comment_lines.append(f"*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return '\n'.join(comment_lines)

def save_pr_comment_for_jenkins(comment_content):
    """Save PR comment in format expected by Jenkins"""
    # Save as Markdown file
    with open('pr_comment_table.md', 'w') as f:
        f.write(comment_content)
    
    # Save as JSON for programmatic use by Jenkins
    comment_data = {
        "body": comment_content,
        "build_number": os.environ.get('BUILD_NUMBER', 'unknown'),
        "build_url": os.environ.get('BUILD_URL', ''),
        "branch": os.environ.get('BRANCH_NAME', 'unknown'),
        "timestamp": datetime.now().isoformat(),
        "format": "markdown_table_python_files"
    }
    
    with open('pr_comment_data.json', 'w') as f:
        json.dump(comment_data, f, indent=2)
    
    print("PR comment files generated:")
    print("- pr_comment_table.md")
    print("- pr_comment_data.json")

def main():
    """Main execution function"""
    print("🧪 Generating Jenkins PR comment with Python test files table...")
    
    # Generate the PR comment
    pr_comment = generate_pr_comment_with_table()
    
    # Save for Jenkins to use
    save_pr_comment_for_jenkins(pr_comment)
    
    # Output preview
    print("\n" + "="*80)
    print("GENERATED PR COMMENT PREVIEW:")
    print("="*80)
    print(pr_comment[:1000] + "..." if len(pr_comment) > 1000 else pr_comment)
    print("="*80)

if __name__ == "__main__":
    main()
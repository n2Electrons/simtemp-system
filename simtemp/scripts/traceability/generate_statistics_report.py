#!/usr/bin/env python3
"""generate_statistics_report.py

Generate comprehensive statistics report from traceability.yml data.
Outputs detailed metrics about requirements, test cases, GitHub integration,
and automation coverage.

Usage:
  python3 simtemp/scripts/generate_statistics_report.py [--out PATH]
  
Arguments:
  --out PATH    Output file path (default: simtemp/reports/statistics_report.md)
"""

import argparse
import yaml
from collections import Counter
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TRACE = BASE_DIR / 'simtemp' / 'reports' / 'traceability.yml'
DEFAULT_OUTPUT = BASE_DIR / 'simtemp' / 'reports' / 'statistics_report.md'


def load_traceability_data(trace_file: Path) -> dict:
    """Load traceability YAML data."""
    if not trace_file.exists():
        raise FileNotFoundError(f"Traceability file not found: {trace_file}")
    
    with open(trace_file, 'r') as f:
        return yaml.safe_load(f)


def calculate_statistics(data: dict) -> dict:
    """Calculate comprehensive statistics from traceability data."""
    requirements = data.get('requirements', [])
    
    # Basic counts
    total_reqs = len(requirements)
    functional_reqs = len([r for r in requirements if r.get('group') == 'functional'])
    non_functional_reqs = len([r for r in requirements if r.get('group') == 'non-functional'])
    
    # Test case statistics
    total_tests = sum(len(r.get('tests', [])) for r in requirements)
    automated_tests = sum(len([t for t in r.get('tests', []) if t.get('automation', False)]) for r in requirements)
    manual_tests = total_tests - automated_tests
    
    # GitHub link statistics
    req_with_github = len([r for r in requirements if r.get('github_link')])
    tests_with_github = sum(len([t for t in r.get('tests', []) if t.get('github_link')]) for r in requirements)
    
    # Module breakdown
    modules = Counter(r.get('module') for r in requirements)
    
    # Status breakdown
    req_statuses = Counter(r.get('status', 'planned') for r in requirements)
    test_statuses = Counter()
    for r in requirements:
        for t in r.get('tests', []):
            test_statuses[t.get('status', 'planned')] += 1
    
    # Module automation coverage
    module_automation = {}
    for module in modules.keys():
        module_reqs = [r for r in requirements if r.get('module') == module]
        module_tests = sum(len(r.get('tests', [])) for r in module_reqs)
        module_automated = sum(len([t for t in r.get('tests', []) if t.get('automation', False)]) for r in module_reqs)
        if module_tests > 0:
            module_automation[module] = {
                'automated': module_automated,
                'total': module_tests,
                'percentage': module_automated / module_tests * 100
            }
    
    return {
        'total_reqs': total_reqs,
        'functional_reqs': functional_reqs,
        'non_functional_reqs': non_functional_reqs,
        'total_tests': total_tests,
        'automated_tests': automated_tests,
        'manual_tests': manual_tests,
        'req_with_github': req_with_github,
        'tests_with_github': tests_with_github,
        'modules': modules,
        'req_statuses': req_statuses,
        'test_statuses': test_statuses,
        'module_automation': module_automation,
        'generated_on': data.get('metadata', {}).get('generated_on', datetime.now().strftime('%Y-%m-%d'))
    }


def generate_report(stats: dict) -> str:
    """Generate markdown report from statistics."""
    report = f"""# Traceability Statistics Report

Generated: {stats['generated_on']}

## Overall Statistics
- **Total Requirements**: {stats['total_reqs']}
  - Functional: {stats['functional_reqs']}
  - Non-Functional: {stats['non_functional_reqs']}
- **Total Test Cases**: {stats['total_tests']}
  - Automated: {stats['automated_tests']} ({stats['automated_tests']/stats['total_tests']*100:.1f}%)
  - Manual: {stats['manual_tests']} ({stats['manual_tests']/stats['total_tests']*100:.1f}%)

## GitHub Integration
- **Requirements with GitHub Links**: {stats['req_with_github']}/{stats['total_reqs']} ({stats['req_with_github']/stats['total_reqs']*100:.1f}%)
- **Test Cases with GitHub Links**: {stats['tests_with_github']}/{stats['total_tests']} ({stats['tests_with_github']/stats['total_tests']*100:.1f}%)

## Module Breakdown
"""

    for module, count in stats['modules'].most_common():
        report += f"- **{module}**: {count} requirements\n"

    report += "\n## Status Overview\n\n### Requirements Status\n"
    for status, count in stats['req_statuses'].most_common():
        report += f"- **{status.title()}**: {count}\n"

    report += "\n### Test Cases Status\n"
    for status, count in stats['test_statuses'].most_common():
        report += f"- **{status.title()}**: {count}\n"

    report += "\n## Automation Coverage by Module\n"
    for module, automation in stats['module_automation'].items():
        report += f"- **{module}**: {automation['automated']}/{automation['total']} ({automation['percentage']:.1f}% automated)\n"

    return report


def main():
    parser = argparse.ArgumentParser(description='Generate traceability statistics report')
    parser.add_argument('--trace-file', type=Path, default=DEFAULT_TRACE,
                       help='Input traceability YAML file')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT,
                       help='Output markdown file')
    args = parser.parse_args()

    try:
        # Load data and calculate statistics
        data = load_traceability_data(args.trace_file)
        stats = calculate_statistics(data)
        
        # Generate and write report
        report = generate_report(stats)
        args.out.write_text(report, encoding='utf-8')
        
        print(f"Generated statistics report: {args.out}")
        print(f"Requirements: {stats['total_reqs']} | Tests: {stats['total_tests']} | Automation: {stats['automated_tests']/stats['total_tests']*100:.1f}%")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
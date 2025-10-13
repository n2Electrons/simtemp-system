#!/usr/bin/env python3
"""show_progress.py

Report requirements and test cases currently marked as in-progress
based on the traceability.yml file, and list active branches that
follow the documented naming structure.

Output Sections:
1. In-Progress Requirements
2. In-Progress Test Cases
3. Git Branch Scan (optional heuristic) - lists local branches matching
   known requirement/test naming patterns (e.g., f-d4-tc-*)

Usage:
  python simtemp/scripts/show_progress.py [--all] [--no-git-scan]
  --all         : include planned items for context
  --no-git-scan : skip scanning for Git branches

Extensibility:
- Add implemented/done states to the STATUS_ORDER for future sorting.
- Integrate with CI to publish as artifact.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except ImportError:
    print("ERROR: PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

BASE_DIR = Path(__file__).resolve().parents[2]
TRACE_FILE = BASE_DIR / 'simtemp' / 'reports' / 'traceability.yml'
BRANCH_PATTERN = re.compile(r'^(f|feat|feature|bugfix|hotfix)-([a-z0-9]+-)?(tc|req)-', re.IGNORECASE)
STATUS_IN_PROGRESS = {'in-progress'}
STATUS_ORDER = ['in-progress', 'planned']
COMPLETED_STATUSES = {'implemented', 'done', 'completed', 'verified'}  # treat any of these as completed


def load_traceability() -> Dict[str, Any]:
    if not TRACE_FILE.exists():
        print(f"ERROR: Traceability file not found: {TRACE_FILE}", file=sys.stderr)
        sys.exit(1)
    with TRACE_FILE.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)  # type: ignore


def collect_progress(data: Dict[str, Any], include_planned=False):
    reqs = data.get('requirements', []) or []
    progress_tree = []
    status_filter = set(STATUS_ORDER) if include_planned else STATUS_IN_PROGRESS
    
    # First build a hierarchical tree
    for r in reqs:
        r_status = r.get('status')
        # Find test cases with matching status
        matching_tests = []
        for t in r.get('tests', []) or []:
            t_status = t.get('status')
            # Only include tests that match our status filter
            if t_status in status_filter:
                matching_tests.append({
                    'id': t.get('id'),
                    'description': t.get('description'),
                    'status': t_status,
                })
        
        # In strict mode (default), only include requirements that:
        # 1. Are themselves in-progress, or
        # 2. Have at least one in-progress test case
        has_in_progress = r_status in STATUS_IN_PROGRESS or any(t.get('status') in STATUS_IN_PROGRESS for t in matching_tests)
        
        if include_planned:
            # In --all mode, include if requirement or any test matches filter
            include_req = r_status in status_filter or matching_tests
        else:
            # In default mode, ONLY include if something is specifically in-progress
            include_req = has_in_progress
            # And filter tests to only show in-progress ones
            matching_tests = [t for t in matching_tests if t['status'] in STATUS_IN_PROGRESS]
        
        if include_req:
            progress_tree.append({
                'id': r.get('id'),
                'summary': r.get('summary'),
                'status': r_status,
                'tests': matching_tests,
                'has_in_progress': has_in_progress
            })
    
    # Sort with in-progress items first, then by ID
    progress_tree.sort(key=lambda x: (0 if x['has_in_progress'] else 1, x['id']))
    return progress_tree

def collect_completed(data: Dict[str, Any]):
    """Collect completed requirements and test cases.

    A requirement is considered completed if its status is in COMPLETED_STATUSES.
    Test cases are considered completed if their status is in COMPLETED_STATUSES.
    We build a tree grouped by requirement. Requirements that have neither a
    completed status nor any completed tests are omitted.
    """
    reqs = data.get('requirements', []) or []
    completed_tree = []
    for r in reqs:
        r_status = r.get('status')
        tests = r.get('tests', []) or []
        completed_tests = [
            {
                'id': t.get('id'),
                'description': t.get('description'),
                'status': t.get('status'),
            }
            for t in tests if t.get('status') in COMPLETED_STATUSES
        ]
        if r_status in COMPLETED_STATUSES or completed_tests:
            completed_tree.append({
                'id': r.get('id'),
                'summary': r.get('summary'),
                'status': r_status if r_status in COMPLETED_STATUSES else 'partial',
                'tests': completed_tests,
            })
    return completed_tree


def list_git_branches() -> List[str]:
    try:
        out = subprocess.check_output(['git', '--no-pager', 'branch'], text=True)
        branches = [line.strip().lstrip('* ').strip() for line in out.splitlines() if line.strip()]
        return branches
    except subprocess.CalledProcessError:
        return []


def filter_prefixed_branches(branches: List[str]):
    return [b for b in branches if BRANCH_PATTERN.search(b)]


def display_tree_view(progress_tree, title):
    """Display a hierarchical tree view of requirements and test cases using Windows-style tree characters."""
    print(f"\n=== {title} ===")
    if not progress_tree:
        print("(none)")
        return
        
    for i, r in enumerate(progress_tree):
        # Determine if this is the last requirement in the list
        is_last_req = i == len(progress_tree) - 1
        
        # Choose the appropriate tree character for the requirement
        req_prefix = "└─" if is_last_req else "├─"
        # Use → for in-progress items, ⏺ for others
        status_marker = "→" if r['status'] in STATUS_IN_PROGRESS else "⏺"
        
        # Print the requirement line
        print(f"{req_prefix} {status_marker} {r['id']}: {r['summary']} (status={r['status']})")
        
        # Handle test cases
        if r['tests']:
            # Print test cases with proper tree characters
            test_indent = "    " if is_last_req else "│   "
            
            for j, t in enumerate(r['tests']):
                is_last_test = j == len(r['tests']) - 1
                test_prefix = "└─" if is_last_test else "├─"
                # Use → for in-progress items, ⏺ for others
                test_marker = "→" if t['status'] in STATUS_IN_PROGRESS else "⏺"
                
                print(f"{test_indent}{test_prefix} {test_marker} {t['id']}: {t['description']} (status={t['status']})")
        else:
            if r['status'] in STATUS_IN_PROGRESS:
                # Print message about no test cases with proper indentation
                test_indent = "    " if is_last_req else "│   "
                print(f"{test_indent}└─ (no in-progress test cases)")


def main():
    parser = argparse.ArgumentParser(description='Show in-progress requirements and test cases.')
    parser.add_argument('--all', action='store_true', help='Include planned items for context')
    parser.add_argument('--no-git-scan', action='store_true', help='Skip scanning for Git branches')
    args = parser.parse_args()

    data = load_traceability()
    progress_tree = collect_progress(data, include_planned=args.all)
    completed_tree = collect_completed(data)
    
    # Only scan Git branches if not disabled
    git_branches = []
    prefixed = []
    if not args.no_git_scan:
        git_branches = list_git_branches()
        prefixed = filter_prefixed_branches(git_branches)

    # Display the hierarchical tree of in-progress items
    title = "Progress Tree (In-Progress and Planned)" if args.all else "Progress Tree (In-Progress Only)"
    display_tree_view(progress_tree, title)

    # Only show Git Branch Scan section if not disabled
    if not args.no_git_scan:
        print("\n=== Git Branch Scan (pattern-matched) ===")
        if prefixed:
            for b in prefixed:
                print(f"- {b}")
        else:
            print("(none)")

    if args.all:
        # Optional extended context
        total_reqs = len(data.get('requirements', []))
        print(f"\nTotal requirements defined: {total_reqs}")

    # Display completed items
    print("\n=== Completed Requirements / Test Cases (Tree) ===")
    if completed_tree:
        for r in sorted(completed_tree, key=lambda x: x['id']):
            print(f"- {r['id']}: {r['summary']} (status={r['status']})")
            if r['tests']:
                for t in r['tests']:
                    print(f"  * {t['id']}: {t['description']} (status={t['status']})")
            else:
                if r['status'] == 'partial':
                    print("  (no completed test cases yet)")
    else:
        print("(none)")

    print("\nDone.")


if __name__ == '__main__':
    main()

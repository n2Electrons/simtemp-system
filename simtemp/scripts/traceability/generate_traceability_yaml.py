#!/usr/bin/env python3
"""generate_traceability_yaml.py

Regenerate YAML structure that maps requirements to tests, preserving
existing requirement & test case statuses, automation flags,
etc. from the existing YAML file (if present).

The script reads test cases from TESTPLAN.md and updates/creates a YAML file
that contains:
    - metadata block
    - requirements block (with their test cases)

NEW: GitHub Integration
    The script can automatically search for GitHub issues related to 
    requirements and test cases, and populate the github_link fields.
    
    Use --github-repo owner/repo to enable GitHub search.
    Use --github-token TOKEN or set GITHUB_TOKEN env var for authentication.
    Without a token, API requests are limited but basic search still works.

NEW: Branch Integration
    The script can automatically map git branches to requirements and test cases:
    - Test cases get a 'branch' field with associated branch name
    - Requirements get a 'branches' list with all related branches
    
    Use --no-branches to disable branch detection.

Usage:
  python simtemp/scripts/generate_traceability_yaml.py            # overwrite file
  python simtemp/scripts/generate_traceability_yaml.py --dry-run  # print to stdout only
  python simtemp/scripts/generate_traceability_yaml.py --out path/to/file.yml
  
  # With GitHub integration:
  python simtemp/scripts/generate_traceability_yaml.py --github-repo owner/repo --github-token TOKEN
  GITHUB_TOKEN=token python simtemp/scripts/generate_traceability_yaml.py --github-repo owner/repo

Limitations:
  - Parses the specific markdown table structure present in TESTPLAN.md (rows are single lines with '|' separators).
  - Does not attempt to infer nuanced expected results beyond what exists already or bullet text.
  - GitHub API rate limits apply (60 requests/hour without token, 5000/hour with token).
"""

from __future__ import annotations
import argparse
import re
import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import yaml  # type: ignore
except ImportError:
    print("ERROR: PyYAML not installed. pip install pyyaml", file=sys.stderr)
    sys.exit(2)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / 'simtemp' / 'reports'
TRACE_PATH = REPORTS_DIR / 'traceability.yml'

TESTPLAN_PATH = BASE_DIR / 'simtemp' / 'docs' / 'TESTPLAN.md'

TEST_ROW_RE = re.compile(r'^\|')
# Updated to match the correct format: F-K#-TC-###, F-U#-TC-###, F-S#-TC-###, F-D#-TC-###, N-F#-TC-###
TC_RE = re.compile(r'(?:F-[KUSD][0-9]+|N-F[0-9]+)-TC-[0-9]{3}')

# Requirement ID patterns based on TESTPLAN.md specification
REQ_ID_PATTERNS = {
    'functional_kernel': re.compile(r'^F-K[0-9]+$'),      # F-K# → Functional / Kernel
    'functional_user': re.compile(r'^F-U[0-9]+$'),        # F-U# → Functional / User Space
    'functional_scripts': re.compile(r'^F-S[0-9]+$'),     # F-S# → Functional / Scripts
    'functional_docs': re.compile(r'^F-D[0-9]+$'),        # F-D# → Functional / Documentation
    'non_functional': re.compile(r'^N-F[0-9]+$'),         # N-F# → Non-Functional requirements
}

# Test Case ID pattern: {REQ_TYPE}-TC-{CASE_NUM} (e.g., F-K1-TC-001, F-U2-TC-002, N-F1-TC-001)
TC_ID_PATTERN = re.compile(r'^((?:F-[KUSD]|N-F)[0-9]+)-TC-([0-9]{3})$')


def validate_and_clean_existing(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean existing YAML data to prevent structure issues."""
    cleaned = {}
    
    # Preserve metadata
    if 'metadata' in data:
        cleaned['metadata'] = data['metadata']
    
    # Clean requirements section
    if 'requirements' in data and isinstance(data['requirements'], list):
        cleaned_reqs = []
        for req in data['requirements']:
            if isinstance(req, dict) and 'id' in req:
                # Ensure tests is a proper list
                if 'tests' in req and isinstance(req['tests'], list):
                    cleaned_tests = []
                    for test in req['tests']:
                        if isinstance(test, dict) and 'id' in test and ('-TC-' in test['id']):
                            cleaned_tests.append(test)
                    req['tests'] = cleaned_tests
                cleaned_reqs.append(req)
        cleaned['requirements'] = cleaned_reqs
    
    return cleaned


def create_backup():
    """Create a backup of existing traceability.yml before overwriting."""
    if TRACE_PATH.exists():
        backup_path = TRACE_PATH.with_suffix('.yml.backup')
        backup_path.write_text(TRACE_PATH.read_text(encoding='utf-8'), encoding='utf-8')
        print(f"Created backup: {backup_path}")


def validate_output_structure(data: Dict[str, Any]) -> bool:
    """Validate the output YAML structure before writing."""
    try:
        # Check basic structure
        if 'requirements' not in data:
            print("ERROR: Missing 'requirements' section", file=sys.stderr)
            return False
        
        # Validate requirements
        for i, req in enumerate(data['requirements']):
            if not isinstance(req, dict) or 'id' not in req:
                print(f"ERROR: Invalid requirement at index {i}", file=sys.stderr)
                return False
            
            if 'tests' in req:
                for j, test in enumerate(req['tests']):
                    if not isinstance(test, dict) or 'id' not in test:
                        print(f"ERROR: Invalid test at req {req['id']}, test index {j}", file=sys.stderr)
                        return False
                    tc_match = TC_ID_PATTERN.match(test['id'])
                    if not tc_match:
                        print(f"ERROR: Invalid test ID format: {test['id']}", file=sys.stderr)
                        return False
        
        return True
    except Exception as e:
        print(f"ERROR: Structure validation failed: {e}", file=sys.stderr)
        return False


def load_existing() -> Dict[str, Any]:
    if not TRACE_PATH.exists():
        return {}
    try:
        with TRACE_PATH.open('r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            # Validate and clean the loaded data
            return validate_and_clean_existing(data)
    except yaml.YAMLError as e:
        print(f"WARNING: Existing YAML is malformed ({e}), starting fresh", file=sys.stderr)
        return {}


def parse_testplan() -> List[Dict[str, Any]]:
    if not TESTPLAN_PATH.exists():
        raise SystemExit(f"TESTPLAN not found: {TESTPLAN_PATH}")
    rows: List[Dict[str, Any]] = []
    in_table = False
    with TESTPLAN_PATH.open('r', encoding='utf-8') as f:
        for line in f:
            if '## 4. Test Cases and Traceability Table' in line:
                in_table = True
                continue
            if in_table:
                if line.strip().startswith('| **#**'):
                    # header line
                    continue
                if line.strip().startswith('|:--:'):
                    continue
                if line.strip().startswith('---') and not line.strip().startswith('|'):
                    # end of table (if separator) - break? table ends earlier though
                    continue
                if not line.strip():
                    # blank after table ends
                    if rows:
                        break
                if TEST_ROW_RE.match(line):
                    parts = [p.strip() for p in line.strip().split('|')]
                    # Expect pattern: ['', number/range, req id, module/sub, description, tests cell, '']
                    if len(parts) < 7:
                        continue
                    req_id = parts[2]
                    module_sub = parts[3]
                    desc = parts[4].rstrip('.')
                    tests_cell = parts[5]
                    # Split module/sub-module
                    if ' / ' in module_sub:
                        module, submodule = [s.strip() for s in module_sub.split(' / ', 1)]
                    else:
                        module, submodule = module_sub, ''
                    # Parse tests from cell
                    tests: List[Dict[str, str]] = []
                    for bullet in tests_cell.replace('<br>', '\n').split('\n'):
                        bullet = bullet.strip(' •')
                        if not bullet:
                            continue
                        m = TC_RE.search(bullet)
                        if not m:
                            continue
                        tc_id = m.group(0)
                        # After **TC-...** → rest
                        # Remove markdown bold markers
                        post = re.sub(r'\*\*' + re.escape(tc_id) + r'\*\*', tc_id, bullet)
                        # Split at arrow
                        if '→' in post:
                            _, rhs = post.split('→', 1)
                        elif '->' in post:
                            _, rhs = post.split('->', 1)
                        else:
                            rhs = post
                        rhs = rhs.strip().strip('.')
                        # description & expected initial (may be overridden by existing)
                        tests.append({
                            'id': tc_id,
                            'description': rhs,
                            'expected': rhs,
                        })
                    rows.append({
                        'id': req_id,
                        'module': module,
                        'submodule': submodule,
                        'summary': desc,
                        'tests': tests,
                    })
    return rows


def build_traceability(parsed: List[Dict[str, Any]], existing: Dict[str, Any]) -> Dict[str, Any]:
    existing_reqs = {r.get('id'): r for r in existing.get('requirements', []) or []}
    existing_tests = {}
    for r in existing.get('requirements', []) or []:
        for t in r.get('tests', []) or []:
            existing_tests[t.get('id')] = t

    out_requirements: List[Dict[str, Any]] = []
    for r in parsed:
        rid = r['id']
        group = 'non-functional' if rid.startswith('N-') else 'functional'
        existing_req = existing_reqs.get(rid, {})
        status = existing_req.get('status')
        new_tests = []
        for t in r['tests']:
            eid = t['id']
            if eid in existing_tests:
                et = existing_tests[eid]
                new_tests.append({
                    'id': et.get('id'),
                    'description': et.get('description', t['description']),
                    'expected': et.get('expected', t['expected']),
                    'status': et.get('status', 'planned'),
                    'automation': et.get('automation', guess_automation(rid)),
                    'github_link': et.get('github_link', ''),
                    'branch': et.get('branch', ''),
                })
            else:
                new_tests.append({
                    'id': eid,
                    'description': t['description'],
                    'expected': t['expected'],
                    'status': 'planned',
                    'automation': guess_automation(rid),
                    'github_link': '',
                    'branch': '',
                })
        req_entry = {
            'id': rid,
            'group': group,
            'module': r['module'],
            'submodule': r['submodule'],
            'summary': r['summary'],
            'priority': existing_req.get('priority', 'Medium'),
            'status': existing_req.get('status', 'planned'),  # Ensure all requirements have status
            'github_link': existing_req.get('github_link', ''),
            'branches': existing_req.get('branches', []),
            'tests': new_tests,
        }
        out_requirements.append(req_entry)

    metadata = existing.get('metadata', {})
    metadata.update({
        'generated_on': datetime.now().strftime('%Y-%m-%d'),
        'source_files': ['simtemp/docs/TESTPLAN.md'],
        'notes': 'Regenerated from TESTPLAN.md via generate_traceability_yaml.py (preserving statuses).'
    })

    # Build result with proper structure order
    result: Dict[str, Any] = {
        'metadata': metadata,
        'requirements': out_requirements,
    }
    
    return result


def guess_automation(req_id: str) -> bool:
    if req_id.startswith('F-D') or req_id == 'F-U5':  # documentation & GUI manual
        return False
    return True


class GitHubSearcher:
    """Search GitHub issues for requirement and test case IDs."""
    
    def __init__(self, repo_owner: str, repo_name: str, token: Optional[str] = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.base_url = "https://api.github.com"
        self.cache = {}  # Cache search results to avoid duplicate API calls
    
    def search_issues(self, query: str) -> List[Dict[str, Any]]:
        """Search GitHub issues for a specific query."""
        if query in self.cache:
            return self.cache[query]
        
        # Construct search query: search in this repo for the specific ID
        search_query = f"{query} repo:{self.repo_owner}/{self.repo_name}"
        encoded_query = urllib.parse.quote(search_query)
        url = f"{self.base_url}/search/issues?q={encoded_query}"
        
        try:
            req = urllib.request.Request(url)
            if self.token:
                req.add_header("Authorization", f"token {self.token}")
            req.add_header("Accept", "application/vnd.github.v3+json")
            req.add_header("User-Agent", "generate_traceability_yaml.py")
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                issues = data.get('items', [])
                self.cache[query] = issues
                return issues
                
        except urllib.error.HTTPError as e:
            if e.code == 403:
                # Don't spam warnings, just cache empty result
                self.cache[query] = []
                return []
            else:
                print(f"WARNING: GitHub API error {e.code} for query '{query}'", file=sys.stderr)
            return []
        except Exception as e:
            print(f"WARNING: Error searching GitHub for '{query}': {e}", file=sys.stderr)
            return []
    
    def find_issue_for_id(self, identifier: str) -> Optional[str]:
        """Find the GitHub issue URL for a requirement or test case ID."""
        # Use the identifier as-is to search GitHub issues
        issues = self.search_issues(identifier)
        
        for issue in issues:
            # Check if the identifier appears in title or body
            title = issue.get('title', '').upper()
            body = issue.get('body', '') or ''
            
            # Look for exact identifier matches with word boundaries
            import re
            pattern = r'\b' + re.escape(identifier) + r'\b'
            
            if (identifier.upper() in title or 
                re.search(pattern, body, re.IGNORECASE)):
                return issue.get('html_url')
        
        return None
    
    def get_issue_status(self, identifier: str) -> Optional[str]:
        """Get the GitHub issue status (open/closed) for a requirement or test case ID."""
        issues = self.search_issues(identifier)
        
        for issue in issues:
            # Check if the identifier appears in title or body
            title = issue.get('title', '').upper()
            body = issue.get('body', '') or ''
            
            # Look for exact identifier matches with word boundaries
            pattern = r'\b' + re.escape(identifier) + r'\b'
            
            if (identifier.upper() in title or 
                re.search(pattern, body, re.IGNORECASE)):
                return issue.get('state')  # Returns 'open' or 'closed'
        
        return None


class BranchMapper:
    """Map git branches to requirement and test case IDs."""
    
    def __init__(self):
        self.branches = self._get_all_branches()
        self.branch_mappings = self._build_branch_mappings()
    
    def _get_all_branches(self) -> List[str]:
        """Get all git branches (local and remote)."""
        try:
            result = subprocess.run(['git', 'branch', '-a'], 
                                    capture_output=True, text=True, check=True)
            branches = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Remove current branch indicator and prefixes
                branch = line.lstrip('* ').replace('remotes/origin/', '')
                if branch and branch != 'HEAD' and '->' not in branch:
                    branches.append(branch)
            # Remove duplicates and sort
            return sorted(list(set(branches)))
        except subprocess.CalledProcessError:
            print("WARNING: Could not retrieve git branches", file=sys.stderr)
            return []
    
    def _build_branch_mappings(self) -> Dict[str, str]:
        """Build mapping from requirement/test case IDs to branch names."""
        mappings = {}
        
        for branch in self.branches:
            branch_upper = branch.upper()
            
            # Pattern 1: f-k1-tc-001-insmod-registers-driver → F-K1-TC-001 and F-K1
            tc_match = re.search(r'([FN])-([KUSD])(\d+)(?:-TC-(\d{3}))?', branch_upper)
            if tc_match:
                prefix = tc_match.group(1)
                module = tc_match.group(2)
                num = tc_match.group(3)
                tc_num = tc_match.group(4)
                
                # Always map the requirement ID
                req_id = f"{prefix}-{module}{num}"
                mappings[req_id] = branch
                
                # Map test case if present
                if tc_num:
                    test_id = f"{req_id}-TC-{tc_num}"
                    mappings[test_id] = branch
                continue
            
            # Pattern 2: f-d4-tc-prompts-recorded → F-D4-TC-001 (if it matches known test)
            # Check for partial matches like f-d4, f-k1, etc.
            req_match = re.search(r'([FN])-([KUSD]?)(\d+)', branch_upper)
            if req_match:
                prefix = req_match.group(1)
                module = req_match.group(2) or ''
                num = req_match.group(3)
                req_id = f"{prefix}-{module}{num}" if module else f"{prefix}-{num}"
                
                # Map the requirement
                mappings[req_id] = branch
                
                # If this is a TC branch, try to infer the test case number
                if '-TC-' in branch_upper or 'TC' in branch.upper():
                    # Look for specific test case patterns in existing data
                    # For now, assume first test case (001) if not specified
                    test_id = f"{req_id}-TC-001"
                    mappings[test_id] = branch
        
        return mappings
    
    def get_branch_for_test(self, test_id: str) -> Optional[str]:
        """Get branch name for a test case ID."""
        return self.branch_mappings.get(test_id)
    
    def get_branches_for_requirement(self, req_id: str, test_ids: List[str]) -> List[str]:
        """Get all branches related to a requirement (direct + from test cases)."""
        branches = []
        
        # Check for direct requirement branch
        req_branch = self.branch_mappings.get(req_id)
        if req_branch:
            branches.append(req_branch)
        
        # Check for test case branches
        for test_id in test_ids:
            test_branch = self.get_branch_for_test(test_id)
            if test_branch and test_branch not in branches:
                branches.append(test_branch)
        
        return sorted(branches)


def populate_github_links(data: Dict[str, Any], github_searcher: Optional[GitHubSearcher]) -> Dict[str, Any]:
    """Populate GitHub links for requirements and test cases if GitHub searcher is provided."""
    if not github_searcher:
        return data
    
    print("Searching GitHub for issues related to requirements and test cases...")
    
    # Process each requirement
    for req in data.get('requirements', []):
        req_id = req.get('id')
        if req_id and not req.get('github_link'):
            github_url = github_searcher.find_issue_for_id(req_id)
            if github_url:
                req['github_link'] = github_url
                print(f"  Found GitHub issue for {req_id}: {github_url}")
        
        # Process each test case
        for test in req.get('tests', []):
            test_id = test.get('id')
            if test_id and not test.get('github_link'):
                github_url = github_searcher.find_issue_for_id(test_id)
                if github_url:
                    test['github_link'] = github_url
                    print(f"  Found GitHub issue for {test_id}: {github_url}")
    
    return data


def update_status_based_on_branches(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update statuses to 'in-progress' for requirements and test cases with associated branches."""
    print("Updating statuses based on branch associations...")
    
    for req in data.get('requirements', []):
        # Check if requirement has associated branches
        req_branches = req.get('branches', [])
        if req_branches:
            req['status'] = 'in-progress'
            print(f"  Set {req['id']} status to 'in-progress' (has branches: {', '.join(req_branches)})")
        
        # Check test cases for branches
        for test in req.get('tests', []):
            test_branch = test.get('branch', '')
            if test_branch:
                test['status'] = 'in-progress'
                print(f"  Set {test['id']} status to 'in-progress' (has branch: {test_branch})")
    
    return data


def populate_branch_info(data: Dict[str, Any], branch_mapper: Optional[BranchMapper], github_searcher: Optional[GitHubSearcher] = None) -> Dict[str, Any]:
    """Populate branch information for requirements and test cases if branch mapper is provided."""
    if not branch_mapper:
        return data
    
    print("Mapping git branches to requirements and test cases...")
    
    # Process each requirement
    for req in data.get('requirements', []):
        req_id = req.get('id')
        if not req_id:
            continue
            
        # Check if this requirement has a direct branch mapping
        req_branch = branch_mapper.branch_mappings.get(req_id)
        if req_branch:
            req['branches'] = [req_branch]
            
            # Only check GitHub status for requirements that have branches
            github_status = None
            if github_searcher:
                github_status = github_searcher.get_issue_status(req_id)
            
            if github_status == 'closed':
                req['status'] = 'implemented'
                print(f"  Found branch for {req_id}: {req_branch} (GitHub issue closed - status: implemented)")
            else:
                req['status'] = 'in-progress'
                print(f"  Found branch for {req_id}: {req_branch} (setting status to in-progress)")
        
        # Process each test case
        for test in req.get('tests', []):
            test_id = test.get('id')
            if test_id:
                test_branch = branch_mapper.branch_mappings.get(test_id)
                if test_branch:
                    test['branch'] = test_branch
                    
                    # Only check GitHub status for test cases that have branches
                    github_status = None
                    if github_searcher:
                        github_status = github_searcher.get_issue_status(test_id)
                    
                    if github_status == 'closed':
                        test['status'] = 'implemented'
                        print(f"  Found branch for {test_id}: {test_branch} (GitHub issue closed - status: implemented)")
                    else:
                        test['status'] = 'in-progress'
                        print(f"  Found branch for {test_id}: {test_branch} (setting status to in-progress)")
                    
                    # Update parent requirement status if not already set
                    if not req_branch and test['status'] == 'in-progress':
                        req['status'] = 'in-progress'
                        print(f"  Setting {req_id} status to in-progress (test {test_id} has branch)")
    
    return data




def main():
    ap = argparse.ArgumentParser(description='Regenerate traceability.yml from TESTPLAN.md')
    ap.add_argument('--out', type=Path, default=TRACE_PATH, help='Output YAML path')
    ap.add_argument('--dry-run', action='store_true', help='Print to stdout instead of writing file')
    ap.add_argument('--no-backup', action='store_true', help='Skip creating backup of existing file')
    ap.add_argument('--debug', action='store_true', help='Enable debug output')
    
    # GitHub integration options
    ap.add_argument('--github-repo', type=str, help='GitHub repository in format owner/repo (e.g., user/my-repo)')
    ap.add_argument('--github-token', type=str, help='GitHub API token (or set GITHUB_TOKEN env var)')
    ap.add_argument('--no-github', action='store_true', help='Skip GitHub issue search even if repo is configured')
    
    # Branch integration options
    ap.add_argument('--no-branches', action='store_true', help='Skip git branch mapping')
    
    args = ap.parse_args()

    # Configure GitHub searcher if requested
    github_searcher = None
    if args.github_repo and not args.no_github:
        if '/' not in args.github_repo:
            print("ERROR: GitHub repo must be in format 'owner/repo'", file=sys.stderr)
            sys.exit(1)
        
        repo_owner, repo_name = args.github_repo.split('/', 1)
        github_token = args.github_token or os.getenv('GITHUB_TOKEN')
        
        if not github_token:
            print("WARNING: No GitHub token provided. API requests will be limited.", file=sys.stderr)
        
        github_searcher = GitHubSearcher(repo_owner, repo_name, github_token)

    # Configure branch mapper if requested
    branch_mapper = None
    if not args.no_branches:
        branch_mapper = BranchMapper()

    try:
        existing = load_existing()
        
        # Regular processing for regenerating YAML
        parsed = parse_testplan()
        trace = build_traceability(parsed, existing)
        
        # Populate GitHub links if searcher is configured
        if github_searcher:
            trace = populate_github_links(trace, github_searcher)
        
        # Populate branch information if mapper is configured
        if branch_mapper:
            trace = populate_branch_info(trace, branch_mapper, github_searcher)
            # Update statuses based on branch associations
            trace = update_status_based_on_branches(trace)
        
        # Validate output structure before writing
        if not validate_output_structure(trace):
            print("ERROR: Generated YAML failed validation. Aborting.", file=sys.stderr)
            sys.exit(1)
        
        yaml_text = yaml.safe_dump(trace, sort_keys=False, default_flow_style=False)
        
        if args.dry_run:
            print(yaml_text)
        else:
            # Create backup unless disabled
            if not args.no_backup:
                create_backup()
            
            args.out.write_text(yaml_text, encoding='utf-8')
            print(f"Wrote {args.out}")
            
            # Verify the written file can be parsed back
            try:
                with args.out.open('r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                print("✓ Output YAML validated successfully")
            except yaml.YAMLError as e:
                print(f"WARNING: Written YAML has parse errors: {e}", file=sys.stderr)
                
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

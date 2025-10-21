#!/usr/bin/env python3
"""update_github_status.py

Script para actualizar automáticamente el status de requirements y test cases
basándose en el estado de los GitHub issues asociados.

Este script:
1. Lee el archivo traceability.yml
2. Para cada requirement/test case con github_link, verifica el estado del issue
3. Si el issue está cerrado, actualiza el status a 'completed'
4. Regenera los reportes de trazabilidad

Uso:
  python simtemp/scripts/traceability/update_github_status.py
  python simtemp/scripts/traceability/update_github_status.py --dry-run
  python simtemp/scripts/traceability/update_github_status.py --github-token TOKEN
"""

import argparse
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml  # type: ignore
except ImportError as e:
    raise SystemExit("PyYAML required: pip install pyyaml") from e

# Import the GitHub searcher from the main script
import sys
sys.path.append(str(Path(__file__).parent))
from generate_traceability_yaml import GitHubSearcher

BASE_DIR = Path(__file__).resolve().parents[2]
REPORTS_DIR = BASE_DIR / 'reports'
TRACE_PATH = REPORTS_DIR / 'traceability.yml'

# Default repositories
DEFAULT_CURRENT_REPO = "n2Electrons/simtemp-system"
DEFAULT_LEGACY_REPO = "n2Electrons/n2Electrons-Infra"


def extract_repo_and_issue(github_url: str) -> Optional[tuple[str, str, int]]:
    """Extract repository and issue number from GitHub URL."""
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)', github_url)
    if match:
        owner, repo, issue_num = match.groups()
        return f"{owner}/{repo}", github_url, int(issue_num)
    return None


def update_statuses_from_github(data: Dict[str, Any], github_token: Optional[str] = None) -> tuple[Dict[str, Any], int]:
    """Update statuses based on GitHub issue states."""
    updates_count = 0
    
    # Collect all unique repositories we need to check
    repos_to_check = set()
    
    for req in data.get('requirements', []):
        github_link = req.get('github_link')
        if github_link:
            repo_info = extract_repo_and_issue(github_link)
            if repo_info:
                repos_to_check.add(repo_info[0])
        
        for test in req.get('tests', []):
            github_link = test.get('github_link')
            if github_link:
                repo_info = extract_repo_and_issue(github_link)
                if repo_info:
                    repos_to_check.add(repo_info[0])
    
    # Create GitHub searchers for each repository
    searchers = {}
    for repo in repos_to_check:
        owner, repo_name = repo.split('/')
        searchers[repo] = GitHubSearcher(owner, repo_name, github_token)
        print(f"Checking repository: {repo}")
    
    # Update requirements
    for req in data.get('requirements', []):
        req_id = req.get('id')
        github_link = req.get('github_link')
        if github_link and req_id:
            repo_info = extract_repo_and_issue(github_link)
            if repo_info:
                repo, url, issue_num = repo_info
                searcher = searchers.get(repo)
                if searcher:
                    status = searcher.get_issue_status(req_id)
                    if status == 'closed' and req.get('status') != 'completed':
                        old_status = req.get('status', 'planned')
                        req['status'] = 'completed'
                        print(f"  Updated {req_id}: {old_status} -> completed (GitHub issue closed)")
                        updates_count += 1
        
        # Update test cases
        for test in req.get('tests', []):
            test_id = test.get('id')
            github_link = test.get('github_link')
            if github_link and test_id:
                repo_info = extract_repo_and_issue(github_link)
                if repo_info:
                    repo, url, issue_num = repo_info
                    searcher = searchers.get(repo)
                    if searcher:
                        status = searcher.get_issue_status(test_id)
                        if status == 'closed' and test.get('status') != 'completed':
                            old_status = test.get('status', 'planned')
                            test['status'] = 'completed'
                            print(f"  Updated {test_id}: {old_status} -> completed (GitHub issue closed)")
                            updates_count += 1
    
    return data, updates_count


def load_traceability(path: Path) -> Dict[str, Any]:
    """Load traceability YAML file."""
    if not path.exists():
        raise SystemExit(f"Traceability file not found: {path}")
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_traceability(data: Dict[str, Any], path: Path) -> None:
    """Save traceability YAML file."""
    # Create backup
    backup_path = path.with_suffix('.yml.backup')
    if path.exists():
        backup_path.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        print(f"Created backup: {backup_path}")
    
    # Write updated data
    yaml_text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
    path.write_text(yaml_text, encoding='utf-8')
    print(f"Updated: {path}")


def regenerate_reports() -> None:
    """Regenerate traceability reports."""
    try:
        script_path = BASE_DIR / 'scripts' / 'traceability' / 'generate_traceability_view.py'
        result = subprocess.run([
            'python3', str(script_path)
        ], cwd=BASE_DIR.parent, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Successfully regenerated traceability reports")
        else:
            print(f"Error regenerating reports: {result.stderr}")
    except Exception as e:
        print(f"Error running report generation: {e}")


def main():
    parser = argparse.ArgumentParser(description="Update GitHub issue statuses in traceability")
    parser.add_argument('--trace-file', type=Path, default=TRACE_PATH,
                        help='Path to traceability.yml file')
    parser.add_argument('--github-token', type=str, 
                        help='GitHub API token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be changed without making changes')
    parser.add_argument('--no-reports', action='store_true',
                        help='Skip regenerating reports after updates')
    
    args = parser.parse_args()
    
    # Get GitHub token
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("WARNING: No GitHub token provided. API requests will be limited.")
    
    print(f"Loading traceability file: {args.trace_file}")
    data = load_traceability(args.trace_file)
    
    print("Checking GitHub issue statuses...")
    updated_data, updates_count = update_statuses_from_github(data, github_token)
    
    if updates_count == 0:
        print("No status updates needed.")
        return
    
    print(f"\nTotal updates: {updates_count}")
    
    if args.dry_run:
        print("DRY RUN: No changes were written to file.")
    else:
        save_traceability(updated_data, args.trace_file)
        
        if not args.no_reports:
            print("\nRegenerating traceability reports...")
            regenerate_reports()
        
        print("\nDone! Check the updated traceability_view_report.html")


if __name__ == '__main__':
    main()
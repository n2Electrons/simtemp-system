#!/usr/bin/env python3
"""fix_github_links.py

Fix GitHub repository links in traceability files to point to the correct repository.
This script automatically updates any GitHub links that point to the wrong repository.

Usage:
  python simtemp/scripts/traceability/fix_github_links.py
  python simtemp/scripts/traceability/fix_github_links.py --dry-run
  python simtemp/scripts/traceability/fix_github_links.py --target-repo n2Electrons/simtemp-system
"""

import argparse
import re
from pathlib import Path
from typing import Dict, Any

try:
    import yaml  # type: ignore
except ImportError as e:
    raise SystemExit("PyYAML required: pip install pyyaml") from e

BASE_DIR = Path(__file__).resolve().parents[2]
REPORTS_DIR = BASE_DIR / 'reports'
TRACE_PATH = REPORTS_DIR / 'traceability.yml'

# Default configuration
DEFAULT_CURRENT_REPO = "n2Electrons/simtemp-system"
DEFAULT_LEGACY_REPO = "n2Electrons/n2Electrons-Infra"

# Issue ranges for repository mapping
LEGACY_ISSUE_RANGE = (1, 65)  # Issues 1-65 are legacy (n2Electrons-Infra)
# Note: Current repo (simtemp-system) uses its own issue numbering from 1+

WRONG_REPOS = [
    "n2Electrons/challenge_2509",
    "n2Electrons/challenge-2509",
]


def load_traceability(path: Path) -> Dict[str, Any]:
    """Load traceability YAML file."""
    if not path.exists():
        raise SystemExit(f"Traceability file not found: {path}")
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_correct_repo_for_issue(issue_number: int, current_repo: str, legacy_repo: str) -> str:
    """Determine the correct repository for an issue based on its number."""
    if LEGACY_ISSUE_RANGE[0] <= issue_number <= LEGACY_ISSUE_RANGE[1]:
        return legacy_repo
    else:
        return current_repo


def fix_github_url(url: str, current_repo: str, legacy_repo: str) -> str:
    """Fix a GitHub URL to point to the correct repository based on issue number."""
    if not url or 'github.com' not in url:
        return url
    
    # Extract issue number from URL
    issue_match = re.search(r'/issues/(\d+)$', url)
    if not issue_match:
        return url
    
    issue_number = int(issue_match.group(1))
    correct_repo = get_correct_repo_for_issue(issue_number, current_repo, legacy_repo)
    return f"https://github.com/{correct_repo}/issues/{issue_number}"


def fix_traceability_data(data: Dict[str, Any], current_repo: str, 
                         legacy_repo: str) -> tuple[Dict[str, Any], int]:
    """Fix GitHub links in traceability data using correct repository mapping."""
    fixes_count = 0
    
    # Process requirements
    for req in data.get('requirements', []):
        github_link = req.get('github_link', '')
        if github_link and any(wrong_repo in github_link for wrong_repo in WRONG_REPOS):
            old_link = github_link
            req['github_link'] = fix_github_url(github_link, current_repo, legacy_repo)
            print(f"Fixed requirement {req.get('id', 'UNKNOWN')}: {old_link} -> {req['github_link']}")
            fixes_count += 1
        
        # Process test cases
        for test in req.get('tests', []):
            github_link = test.get('github_link', '')
            if github_link and any(wrong_repo in github_link for wrong_repo in WRONG_REPOS):
                old_link = github_link
                test['github_link'] = fix_github_url(github_link, current_repo, legacy_repo)
                print(f"Fixed test {test.get('id', 'UNKNOWN')}: {old_link} -> {test['github_link']}")
                fixes_count += 1
    
    return data, fixes_count


def main():
    parser = argparse.ArgumentParser(description="Fix GitHub repository links")
    parser.add_argument('--trace-file', type=Path, default=TRACE_PATH,
                        help='Path to traceability.yml file')
    parser.add_argument('--current-repo', type=str, default=DEFAULT_CURRENT_REPO,
                        help='Current repository in format owner/repo')
    parser.add_argument('--legacy-repo', type=str, default=DEFAULT_LEGACY_REPO,
                        help='Legacy repository in format owner/repo')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show changes without making them')
    
    args = parser.parse_args()
    
    if '/' not in args.current_repo or '/' not in args.legacy_repo:
        raise SystemExit("Repositories must be in format 'owner/repo'")
    
    print(f"Loading traceability file: {args.trace_file}")
    data = load_traceability(args.trace_file)
    
    print(f"Mapping issues to repositories:")
    print(f"  Legacy issues {LEGACY_ISSUE_RANGE[0]}-{LEGACY_ISSUE_RANGE[1]}: {args.legacy_repo}")
    print(f"  All other issues: {args.current_repo}")
    
    fixed_data, fixes_count = fix_traceability_data(data, args.current_repo, args.legacy_repo)
    
    if fixes_count == 0:
        print("No GitHub links needed fixing.")
        return
    
    print(f"\nTotal fixes applied: {fixes_count}")
    
    if args.dry_run:
        print("DRY RUN: No changes were written to file.")
    else:
        # Create backup
        backup_path = args.trace_file.with_suffix('.yml.backup')
        backup_content = args.trace_file.read_text(encoding='utf-8')
        backup_path.write_text(backup_content, encoding='utf-8')
        print(f"Created backup: {backup_path}")
        
        # Write fixed data
        yaml_text = yaml.safe_dump(fixed_data, sort_keys=False, 
                                   default_flow_style=False)
        args.trace_file.write_text(yaml_text, encoding='utf-8')
        print(f"Updated: {args.trace_file}")
        
        print("\nNext steps:")
        print("1. Regenerate traceability reports:")
        print("   python simtemp/scripts/traceability/generate_traceability_view.py")
        print("2. Verify the HTML report has correct links:")
        print("   Open simtemp/reports/traceability_view_report.html")


if __name__ == '__main__':
    main()
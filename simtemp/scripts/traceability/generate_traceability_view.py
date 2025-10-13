#!/usr/bin/env python3
"""generate_traceability_view.py

Generate graphical traceability artifacts
    lines.append('.req { margin: .3rem 0; padding: .4rem; border: 1px solid #ccc; border-radius: 4px; display: flex; align-items: center; }')
    lines.append('.req-number { width: 60px; font-weight: bold; color: #333; font-size: .9rem; margin-right: 0.8rem; text-align: center; }')
    lines.append('.req-content { flex: 1; }')
    lines.append('.tests { margin-left: 6rem; margin-top: .3rem; }')
 1. HTML hierarchical expandable tree (requirements → test cases) with status colors.
 2. Mermaid diagram source (flowchart) linking requirements to their test cases.
 3. JSON export (hierarchy + simple aggregates) suitable for Grafana (Infinity / JSON plugin).

Outputs (written alongside this script by default):
    - traceability_view_report.html (HTML interactive tree)
    - traceability_report.mmd (Mermaid diagram source)
    - traceability_report.json (JSON hierarchy + aggregates)
    - traceability_report.yml (YAML export of processed/normalized data)

Usage:
  python simtemp/scripts/generate_traceability_view.py [--trace-file PATH] [--out-dir DIR]

Flags:
  --trace-file   Override path to traceability.yml
  --out-dir      Directory for generated artifacts (default: simtemp/reports)
    --no-mermaid   Skip generation of Mermaid file
    --no-json      Skip JSON export
    --no-yaml      Skip YAML normalized export

Status Color Legend (default mapping):
  planned: #d0d7de (gray)
  in-progress: #fff3cd (amber)
  implemented / done / completed / verified: #d1e7dd (green)
  partial (derived when some tests done): #cfe2ff (blue)
  other: #f8d7da (red fallback)

Grafana Option:
  Import traceability.json via a JSON/Infinity data source and build panels:
    - Table: requirements (id, summary, status, test_count, done_count)
    - Stat: % tests completed = sum(done_count)/sum(test_count)
    - Bar: tests per status (expand tests array)

This script is intentionally dependency-light (only PyYAML) for portability.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import html

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from e

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TRACE = BASE_DIR / 'simtemp' / 'reports' / 'traceability.yml'
SCRIPT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / 'simtemp' / 'reports'

COMPLETED_STATUSES = {"implemented", "done", "completed", "verified"}

STATUS_COLORS = {
    'planned': '#f8f9fa',      # Very light gray
    'in-progress': '#fff3cd',  # Light yellow
    'implemented': '#d1e7dd',  # Light green
    'verified': '#d4edda',     # Slightly darker green
    'blocked': '#f8d7da',      # Light red
    'partial': "#d1d8e7",      # Light blue (brighter)
}


def load_traceability(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Traceability file not found: {path}")
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)  # type: ignore


def derive_requirement_status(req: Dict[str, Any]) -> str:
    explicit = req.get('status')
    tests = req.get('tests', []) or []
    completed = sum(1 for t in tests if t.get('status') in COMPLETED_STATUSES)
    total = len(tests)
    if explicit in COMPLETED_STATUSES:
        return explicit
    if completed and completed < total:
        return 'partial'
    return explicit or 'planned'


def get_github_repo_url(data: Dict[str, Any]) -> str:
    """Extract GitHub repository URL from existing GitHub links."""
    # Check requirements for GitHub links to extract repo URL
    for req in data.get('requirements', []):
        github_link = req.get('github_link', '')
        if github_link and 'github.com' in github_link:
            # Extract base repo URL from issue link
            # https://github.com/owner/repo/issues/123 -> https://github.com/owner/repo
            parts = github_link.split('/')
            if len(parts) >= 5 and 'github.com' in github_link:
                return '/'.join(parts[:5])  # protocol://github.com/owner/repo
        
        # Check test cases for GitHub links
        for test in req.get('tests', []):
            github_link = test.get('github_link', '')
            if github_link and 'github.com' in github_link:
                parts = github_link.split('/')
                if len(parts) >= 5:
                    return '/'.join(parts[:5])
    
    return ''


def build_html(data: Dict[str, Any]) -> str:
    reqs = data.get('requirements', []) or []
    lines: List[str] = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html lang="en"><head><meta charset="UTF-8"/>')
    lines.append('<title>Traceability View</title>')
    lines.append('<style>')
    lines.append('body { font-family: Arial, Helvetica, sans-serif; margin: 1.2rem; }')
    lines.append('.req { margin: .3rem 0; padding: .4rem; border: 1px solid #ccc; border-radius: 4px; display: flex; align-items: center; }')
    lines.append('.req-number { width: 60px; font-weight: bold; color: #333; font-size: .9rem; margin-right: 0.8rem; text-align: center; }')
    lines.append('.req-content { flex: 1; }')
    lines.append('.tests { margin-left: 4.5rem; margin-top: .3rem; }')
    lines.append('.test { margin: .15rem 0; padding: .25rem .4rem .25rem 1.5rem; border-left: 3px solid #888; }')
    lines.append('.status-pill { display: inline-block; padding: 2px 6px; font-size: .7rem; border-radius: 10px; background: #eee; margin-left: .4rem; }')
    lines.append('.toggle { cursor: pointer; font-weight: bold; }')
    lines.append('.counts { font-size: .75rem; color: #555; margin-left: .5rem; }')
    lines.append('.legend span { display: inline-block; margin-right: 1rem; font-size: .75rem; padding: 3px 6px; border-radius: 4px; }')
    lines.append('.gh-link { display: inline-block; text-decoration: none; color: #0969da; font-size: 0.9rem; margin-left: 0.3rem; }')
    lines.append('.gh-link:hover { color: #0969da; text-decoration: underline; }')
    lines.append('.branch-link { display: inline-block; text-decoration: none; color: #8250df; font-size: 0.8rem; margin-left: 0.3rem; }')
    lines.append('.branch-link:hover { color: #8250df; text-decoration: underline; }')
    lines.append('.summary { font-size: .85rem; color: #222; margin-bottom: .8rem; }')
    lines.append('</style>')
    # Inline script
    lines.append('<script>'
                 'function tg(id){const e=document.getElementById(id);if(!e)return;'
                 'e.style.display=(e.style.display==="none"?"block":"none");}'
                 '</script>')
    lines.append('</head><body>')
    # Legend
    lines.append('<h1>Requirements ↔ Test Cases Traceability</h1>')
    legend_html = ''.join(
        f'<span style="background:{color}">{html.escape(status)}</span>' for status, color in STATUS_COLORS.items()
    )
    # Add GitHub link indicator to legend
    legend_html += '<span>🔗 = GitHub Issue</span>'
    legend_html += '<span>🌿 = Git Branch</span>'
    lines.append(f'<div class="legend">{legend_html}</div>')

    total_reqs = len(reqs)
    total_tests = sum(len(r.get('tests', []) or []) for r in reqs)
    completed_tests = sum(1 for r in reqs for t in (r.get('tests', []) or []) if t.get('status') in COMPLETED_STATUSES)
    lines.append(f'<div class="summary">Requirements: {total_reqs} | Tests: {total_tests} | Completed Tests: {completed_tests} ({(completed_tests/total_tests*100 if total_tests else 0):.1f}%)</div>')

    # Track absolute test case counter across all requirements
    absolute_tc_number = 0
    
    for idx, r in enumerate(reqs):
        r_id = r.get('id')
        r_sum = r.get('summary')
        r_status = derive_requirement_status(r)
        tests = r.get('tests', []) or []
        test_done = sum(1 for t in tests if t.get('status') in COMPLETED_STATUSES)
        color = STATUS_COLORS.get(r_status, '#f8d7da')
        div_id = f"tests_{idx}"  # stable index based id
        
        # Calculate test case range for this requirement
        start_tc = absolute_tc_number + 1
        end_tc = absolute_tc_number + len(tests)
        if len(tests) == 0:
            tc_range = "0"
        elif len(tests) == 1:
            tc_range = str(start_tc)
        else:
            tc_range = f"{start_tc}-{end_tc}"
        
        lines.append(f'<div class="req" style="background:{color}">')
        lines.append(f'<div class="req-number">{tc_range}</div>')
        lines.append(f'<div class="req-content">')
        lines.append(f'<span class="toggle" onclick="tg(\'{div_id}\')">▸</span> <strong>{html.escape(r_id)}</strong>: {html.escape(r_sum)}')
        
        # Add GitHub issue link if available
        github_url = r.get('github_issue_url') or r.get('github_link')
        if github_url:
            issue_title = r.get('github_issue', 'GitHub Issue')
            lines.append(f' <a href="{html.escape(github_url)}" target="_blank" title="{html.escape(issue_title)}" class="gh-link">🔗</a>')
        
        lines.append(f'<span class="status-pill">{html.escape(r_status)}</span>')
        lines.append(f'<span class="counts">({test_done}/{len(tests)} tests completed)</span>')
        lines.append(f'</div>')
        lines.append(f'</div>')
        lines.append(f'<div class="tests" id="{div_id}" style="display:none">')
        for t in tests:
            absolute_tc_number += 1
            t_id = t.get('id')
            t_desc = t.get('description')
            t_status = t.get('status') or 'planned'
            t_color = STATUS_COLORS.get(t_status, '#f8d7da')
            
            # Start building the test case HTML
            test_html = f'<div class="test" style="background:{t_color}">'
            test_html += f'<strong>{html.escape(t_id)}</strong>: {html.escape(t_desc)}'
            
            # Add GitHub issue link for test case if available
            github_test_url = t.get('github_issue_url') or t.get('github_link')
            if github_test_url:
                t_issue_title = t.get('github_issue', f'GitHub Issue for {t_id}')
                test_html += f' <a href="{html.escape(github_test_url)}" target="_blank" title="{html.escape(t_issue_title)}" class="gh-link">🔗</a>'
            # Also check if there's a GitHub issue specifically for this test case in github_issues list
            else:
                # Look through github_issues section for matching test case
                github_issues = data.get('github_issues', []) or []
                for issue in github_issues:
                    if issue.get('test_case') == t_id:
                        issue_url = issue.get('url')
                        issue_title = issue.get('title', f'GitHub Issue for {t_id}')
                        if issue_url:  # Only add if URL exists
                            test_html += f' <a href="{html.escape(issue_url)}" target="_blank" title="{html.escape(issue_title)}" class="gh-link">🔗</a>'
                            break
            
            # Add branch link for test case if available
            branch_name = t.get('branch', '')
            if branch_name:
                github_repo_url = get_github_repo_url(data)
                if github_repo_url:
                    branch_url = f"{github_repo_url}/tree/{branch_name}"
                    test_html += f' <a href="{html.escape(branch_url)}" target="_blank" title="Git branch: {html.escape(branch_name)}" class="branch-link">🌿</a>'
            
            test_html += f' <span class="status-pill">{html.escape(t_status)}</span></div>'
            lines.append(test_html)
        lines.append('</div>')  # tests

    # Mermaid embed (optional if file exists) - we inline placeholder referencing external .mmd
    lines.append('<h2>Mermaid Diagram</h2>')
    lines.append('<p>This is a flowchart representation of Requirement → Test Case relationships.</p>')
    lines.append('<pre><code id="mermaid-code" class="language-mermaid"></code></pre>')
    lines.append('<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>')
    lines.append('<script>fetch("traceability.mmd").then(r=>r.text()).then(txt=>{document.getElementById("mermaid-code").textContent=txt; mermaid.initialize({startOnLoad:true});});</script>')

    lines.append('</body></html>')
    return '\n'.join(lines)


def build_mermaid(data: Dict[str, Any]) -> str:
    reqs = data.get('requirements', []) or []
    lines = ["flowchart LR", '%% Requirement to Test Case relationships']
    for r in reqs:
        rid = r.get('id')
        rlabel = rid
        
        # Add GitHub link to Mermaid if available
        if 'github_issue_url' in r:
            # Use click directive to make node clickable with GitHub link
            lines.append(f'{rid}["{rlabel} 🔗"]')
            lines.append(f'click {rid} "{r["github_issue_url"]}" _blank')
        else:
            lines.append(f'{rid}["{rlabel}"]')
        for t in r.get('tests', []) or []:
            tid = t.get('id')
            # Simplify id for Mermaid (no dashes) to avoid parser confusion
            safe_tid = tid.replace('-', '_')
            
            # Add GitHub link icon to test case if available
            if 'github_issue_url' in t:
                lines.append(f'{safe_tid}("{tid} 🔗")')
                lines.append(f'click {safe_tid} "{t["github_issue_url"]}" _blank')
            else:
                # Look through github_issues section for matching test case
                github_issues = data.get('github_issues', []) or []
                found_issue = False
                for issue in github_issues:
                    if issue.get('test_case') == tid and issue.get('url'):
                        lines.append(f'{safe_tid}("{tid} 🔗")')
                        lines.append(f'click {safe_tid} "{issue["url"]}" _blank')
                        found_issue = True
                        break
                if not found_issue:
                    lines.append(f'{safe_tid}("{tid}")')
            
            lines.append(f'{rid} --> {safe_tid}')
    return '\n'.join(lines)


def build_json(data: Dict[str, Any]) -> Dict[str, Any]:
    reqs = data.get('requirements', []) or []
    out: List[Dict[str, Any]] = []
    for r in reqs:
        tests = r.get('tests', []) or []
        test_objs = []
        done_count = 0
        for t in tests:
            status = t.get('status') or 'planned'
            if status in COMPLETED_STATUSES:
                done_count += 1
                
            # Create test case object with base fields
            test_obj = {
                'id': t.get('id'),
                'description': t.get('description'),
                'status': status,
            }
            
            # Add GitHub issue information if available for this test case
            if 'github_issue' in t:
                test_obj['github_issue'] = t.get('github_issue')
            if 'github_issue_url' in t:
                test_obj['github_issue_url'] = t.get('github_issue_url')
                
            # If no direct GitHub issue, check in github_issues list
            if 'github_issue_url' not in test_obj:
                github_issues = data.get('github_issues', []) or []
                for issue in github_issues:
                    if issue.get('test_case') == t.get('id'):
                        if issue.get('title'):
                            test_obj['github_issue'] = issue.get('title')
                        if issue.get('url'):
                            test_obj['github_issue_url'] = issue.get('url')
                        break
                
            test_objs.append(test_obj)
        req_status = derive_requirement_status(r)
        # Create requirement object with base fields
        req_obj = {
            'id': r.get('id'),
            'summary': r.get('summary'),
            'status': req_status,
            'test_count': len(tests),
            'done_count': done_count,
            'tests': test_objs,
        }
        
        # Add GitHub issue information if available
        if 'github_issue' in r:
            req_obj['github_issue'] = r.get('github_issue')
        if 'github_issue_url' in r:
            req_obj['github_issue_url'] = r.get('github_issue_url')
            
        out.append(req_obj)
    completed_tests = sum(x['done_count'] for x in out)
    total_tests = sum(x['test_count'] for x in out)
    agg = {
        'requirements_total': len(out),
        'tests_total': total_tests,
        'tests_completed': completed_tests,
        'tests_completed_pct': (completed_tests / total_tests * 100 if total_tests else 0),
    }
    return {'requirements': out, 'aggregate': agg}


def main():
    p = argparse.ArgumentParser(description="Generate graphical traceability view")
    p.add_argument('--trace-file', type=Path, default=DEFAULT_TRACE)
    p.add_argument('--out-dir', type=Path, default=REPORTS_DIR)
    p.add_argument('--no-mermaid', action='store_true')
    p.add_argument('--no-json', action='store_true')
    p.add_argument('--no-yaml', action='store_true')
    args = p.parse_args()

    data = load_traceability(args.trace_file)
    
    # Debug: Print requirements with GitHub issues
    print("Debug: Checking for GitHub issues in requirements...")
    for req in data.get('requirements', []):
        if 'github_issue' in req or 'github_issue_url' in req:
            print(f"  Found GitHub issue for requirement {req.get('id')}: {req.get('github_issue', 'No title')} / {req.get('github_issue_url', 'No URL')}")
        
        # Check test cases
        for test in req.get('tests', []):
            if 'github_issue' in test or 'github_issue_url' in test:
                print(f"  Found GitHub issue for test case {test.get('id')}: {test.get('github_issue', 'No title')} / {test.get('github_issue_url', 'No URL')}")
    
    # Debug: Print github_issues section
    if 'github_issues' in data:
        print(f"\nDebug: Found {len(data['github_issues'])} GitHub issues in github_issues section")
        for issue in data['github_issues']:
            print(f"  Issue: {issue.get('title')} - Req: {issue.get('requirement')} - Test: {issue.get('test_case')}")

    html_content = build_html(data)
    html_path = args.out_dir / 'traceability_view_report.html'
    html_path.write_text(html_content, encoding='utf-8')

    if not args.no_mermaid:
        mermaid_src = build_mermaid(data)
        (args.out_dir / 'traceability_report.mmd').write_text(mermaid_src, encoding='utf-8')

    if not args.no_json:
        json_obj = build_json(data)
        (args.out_dir / 'traceability_report.json').write_text(json.dumps(json_obj, indent=2), encoding='utf-8')
        if not args.no_yaml:
            # Write a YAML version mirroring JSON for tooling that prefers YAML naming convention
            try:
                (args.out_dir / 'traceability_report.yml').write_text(
                    yaml.safe_dump(json_obj, sort_keys=False), encoding='utf-8'
                )
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed to write YAML export: {e}")

    print(f"Generated: {html_path}")
    if not args.no_mermaid:
        print(f"Generated: {(args.out_dir / 'traceability_report.mmd')} (Mermaid)")
    if not args.no_json:
        print(f"Generated: {(args.out_dir / 'traceability_report.json')} (JSON)")
        if not args.no_yaml:
            print(f"Generated: {(args.out_dir / 'traceability_report.yml')} (YAML)")


if __name__ == '__main__':
    main()

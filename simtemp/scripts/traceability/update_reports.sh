#!/bin/bash
#
# update_reports.sh - Simple script to update all traceability reports
#
# This script:
# 1. Updates traceability.yml with GitHub status (using gh CLI)
# 2. Generates HTML, JSON, and Mermaid reports
#
# Usage: ./update_reports.sh [--dry-run]
#

set -e  # Exit on any error

# Parse command line arguments
DRY_RUN=""
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
fi

# Get script directory and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "UPDATING TRACEABILITY REPORTS"
echo "================================================================================"

# Step 1: Update traceability.yml with GitHub status
echo ""
echo "STEP 1: Updating traceability.yml with GitHub information..."
echo "Command: python3 generate_traceability_yaml.py --github-repo n2Electrons/n2Electrons-Infra $DRY_RUN"

if [[ -n "$DRY_RUN" ]]; then
    python3 generate_traceability_yaml.py --github-repo n2Electrons/n2Electrons-Infra $DRY_RUN
else
    python3 generate_traceability_yaml.py --github-repo n2Electrons/n2Electrons-Infra
fi

# Step 2: Generate HTML/JSON/Mermaid reports (only if not dry run)
if [[ -z "$DRY_RUN" ]]; then
    echo ""
    echo "STEP 2: Generating HTML, JSON, and Mermaid reports..."
    echo "Command: python3 generate_traceability_view.py"
    python3 generate_traceability_view.py
fi

# Final message
echo ""
echo "================================================================================"
if [[ -n "$DRY_RUN" ]]; then
    echo "DRY RUN COMPLETE - No files were modified"
else
    echo "REPORTS UPDATE COMPLETE"
    echo ""
    echo "Generated files:"
    echo "  - Main config: simtemp/reports/traceability.yml"
    echo "  - HTML report: simtemp/reports/traceability_view_report.html"
    echo "  - JSON report: simtemp/reports/traceability_report.json"
    echo "  - Mermaid diagram: simtemp/reports/traceability_report.mmd"
    echo "  - YAML summary: simtemp/reports/traceability_report.yml"
fi
echo "================================================================================"

exit 0
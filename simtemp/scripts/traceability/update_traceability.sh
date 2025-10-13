#!/bin/bash
#
# update_traceability.sh - Update traceability.yml with GitHub links and generate reports
#
# This script:
# 1. Searches GitHub for issues matching requirement and test case patterns
# 2. Updates traceability.yml with the found GitHub issue links
# 3. Shows a comprehensive summary of the GitHub search results
# 4. Generates traceability view (HTML report)
# 5. Generates statistics report
#
# Usage:
#   ./simtemp/scripts/update_traceability.sh [--dry-run] [--verbose]
#

set -e  # Exit on any error

# Default options
DRY_RUN=false
VERBOSE=false

# Find workspace root
find_workspace_root() {
    local current_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Look for workspace indicators going up the directory tree
    while [[ "$current_dir" != "/" ]]; do
        if [[ -d "$current_dir/simtemp" && -d "$current_dir/infra" ]]; then
            echo "$current_dir"
            return 0
        fi
        if [[ -f "$current_dir/Jenkinsfile" && -f "$current_dir/README.md" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done
    
    # Fallback to current directory
    pwd
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--verbose]"
            echo ""
            echo "Update traceability.yml with GitHub links and generate reports"
            echo ""
            echo "This script performs 5 steps:"
            echo "  1. Search GitHub for requirement/test case patterns"
            echo "  2. Update traceability.yml with GitHub issue links"
            echo "  3. Show comprehensive GitHub search summary"
            echo "  4. Generate traceability view (HTML report)"
            echo "  5. Generate statistics report (Markdown)"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be updated without making changes"
            echo "  --verbose    Show detailed progress information"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Find workspace root
WORKSPACE_ROOT=$(find_workspace_root)
echo "Workspace root: $WORKSPACE_ROOT"

# Define script paths
GITHUB_SEARCH_SCRIPT="$WORKSPACE_ROOT/infra/scripts/github/github_pattern_search_cli.py"
GITHUB_UPDATE_SCRIPT="$WORKSPACE_ROOT/infra/scripts/github/update_traceability_github_links.py"
GITHUB_SUMMARY_SCRIPT="$WORKSPACE_ROOT/infra/scripts/github/github_pattern_search_summary.py"
TRACEABILITY_VIEW_SCRIPT="$WORKSPACE_ROOT/simtemp/scripts/generate_traceability_view.py"
STATISTICS_REPORT_SCRIPT="$WORKSPACE_ROOT/simtemp/scripts/generate_statistics_report.py"

# Verify scripts exist
if [[ ! -f "$GITHUB_SEARCH_SCRIPT" ]]; then
    echo "Error: GitHub search script not found: $GITHUB_SEARCH_SCRIPT"
    exit 1
fi

if [[ ! -f "$GITHUB_UPDATE_SCRIPT" ]]; then
    echo "Error: GitHub update script not found: $GITHUB_UPDATE_SCRIPT"
    exit 1
fi

# Start the process
echo "================================================================================"
echo "UPDATING TRACEABILITY.YML WITH GITHUB LINKS"
echo "================================================================================"

# Step 1: Search GitHub for issues with patterns
echo ""
echo "STEP 1: Search GitHub for requirement and test case patterns"
echo "Searching GitHub issues for requirement and test case patterns"

SEARCH_CMD="python3 $GITHUB_SEARCH_SCRIPT"
if [[ "$VERBOSE" == "true" ]]; then
    SEARCH_CMD="$SEARCH_CMD --verbose"
fi

echo "Command: $SEARCH_CMD"
if ! $SEARCH_CMD; then
    echo "Error: GitHub search failed!"
    exit 1
fi

echo "GitHub search completed successfully"

# Step 2: Update traceability.yml with found GitHub links
echo ""
echo "STEP 2: Update traceability.yml with GitHub issue links"
echo "Updating traceability.yml with GitHub issue links"

UPDATE_CMD="python3 $GITHUB_UPDATE_SCRIPT"
if [[ "$DRY_RUN" == "true" ]]; then
    UPDATE_CMD="$UPDATE_CMD --dry-run"
fi
if [[ "$VERBOSE" == "true" ]]; then
    UPDATE_CMD="$UPDATE_CMD --verbose"
fi

echo "Command: $UPDATE_CMD"
if ! $UPDATE_CMD; then
    echo "Error: Traceability update failed!"
    exit 1
fi

echo "Traceability update completed successfully"

# Step 3: Show summary (optional, don't fail if it doesn't work)
echo ""
echo "STEP 3: Show comprehensive summary"
if [[ -f "$GITHUB_SUMMARY_SCRIPT" ]]; then
    echo "Showing GitHub pattern search summary"
    echo "Command: python3 $GITHUB_SUMMARY_SCRIPT"
    
    # Don't exit on summary failure
    if python3 "$GITHUB_SUMMARY_SCRIPT"; then
        echo "Summary displayed successfully"
    else
        echo "Warning: Summary script failed, but that's okay"
    fi
else
    echo "Warning: Summary script not found, skipping"
fi

# Step 4: Generate traceability view
echo ""
echo "STEP 4: Generate traceability view"
if [[ -f "$TRACEABILITY_VIEW_SCRIPT" ]]; then
    echo "Generating traceability view"
    echo "Command: python3 $TRACEABILITY_VIEW_SCRIPT"
    
    # Don't exit on view generation failure
    if python3 "$TRACEABILITY_VIEW_SCRIPT"; then
        echo "Traceability view generated successfully"
    else
        echo "Warning: Traceability view generation failed, but continuing"
    fi
else
    echo "Warning: Traceability view script not found, skipping"
fi

# Step 5: Generate statistics report
echo ""
echo "STEP 5: Generate statistics report"
if [[ -f "$STATISTICS_REPORT_SCRIPT" ]]; then
    echo "Generating statistics report"
    echo "Command: python3 $STATISTICS_REPORT_SCRIPT"
    
    # Don't exit on statistics generation failure
    if python3 "$STATISTICS_REPORT_SCRIPT"; then
        echo "Statistics report generated successfully"
    else
        echo "Warning: Statistics report generation failed, but continuing"
    fi
else
    echo "Warning: Statistics report script not found, skipping"
fi

# Final message
echo ""
echo "================================================================================"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "DRY RUN COMPLETE - No files were modified"
else
    echo "TRACEABILITY UPDATE COMPLETE"
fi
echo "================================================================================"
echo "traceability.yml has been updated with GitHub issue links!"
echo "Check simtemp/reports/traceability.yml for the updated links."
echo "Generated reports:"
echo "  - Traceability view: simtemp/reports/traceability_view_report.html"
echo "  - Statistics report: simtemp/reports/statistics_report.md"

exit 0
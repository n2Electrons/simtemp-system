#!/bin/bash
# Local test runner for simtemp project
# Executes pytest for kernel module tests
#
# NOTE: This script is primarily for manual/local testing and legacy compatibility.
# For Jenkins CI/CD, the enhanced Python test report generator is used:
# - Jenkins uses: create_detailed_test_report.py (generates detailed reports with test status)
# - Manual use: run_tests.sh (simple pytest execution) or create_detailed_test_report.py
#
# This script is designed to work in multiple environments:
# - Jenkins containers with pre-installed system packages (preferred)
# - Local development environments with virtual environments
# - CI/CD environments where dependencies are managed externally
#
# The script automatically detects available Python packages and uses
# system packages when available, falling back to virtual environment
# only when necessary.

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting simtemp test suite...${NC}"

# Verify we have python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    echo "Please ensure python3 is installed in the environment"
    exit 1
fi

# Run the tests
echo -e "${YELLOW}Running tests...${NC}"
cd "$SCRIPT_DIR"

# Create results directory if it doesn't exist
mkdir -p results

# Run pytest with various useful flags:
# -v: verbose output
# --tb=short: shorter traceback
# -rA: show all test results summary
python3 -m pytest \
    -v \
    --tb=short \
    -rA \
    test_f_k1_tc_001.py \
    "$@"

TEST_EXIT_CODE=$?

# Deactivate virtual environment if we used one
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed. Check the output above for details.${NC}"
fi

exit $TEST_EXIT_CODE
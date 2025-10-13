#!/bin/bash
# cleanup_permissions.sh
# Script to reset permissions on kernel module build artifacts
# This ensures Jenkins can clean up the workspace after builds

set -e

# Get the workspace root (default to current directory if not set)
WORKSPACE_ROOT="${WORKSPACE:-$(pwd)}"
OBJ_DIR="${WORKSPACE_ROOT}/simtemp/kernel/obj"

echo "Cleaning up permissions in ${OBJ_DIR}"

# Check if the directory exists
if [ -d "${OBJ_DIR}" ]; then
    echo "Resetting ownership of kernel build artifacts to Jenkins user"
    
    # Fix permissions on all files in the obj directory
    if [ -n "$(which sudo)" ]; then
        # If sudo is available, use it to change ownership recursively
        sudo chown -R jenkins:jenkins "${OBJ_DIR}" || true
        sudo chmod -R u+rw "${OBJ_DIR}" || true
    else
        echo "Warning: sudo not available, attempting direct chmod"
        # If sudo is not available, try to make files readable/writable for everyone
        chmod -R a+rw "${OBJ_DIR}" || true
    fi
    
    echo "Cleanup complete"
else
    echo "Object directory ${OBJ_DIR} not found, nothing to clean"
fi

# Also handle potential root-owned files in the tests directory
TEST_DIR="${WORKSPACE_ROOT}/simtemp/tests"
if [ -d "${TEST_DIR}" ]; then
    echo "Checking for root-owned files in test directory"
    if [ -n "$(which sudo)" ]; then
        sudo chown -R jenkins:jenkins "${TEST_DIR}" || true
    else
        chmod -R a+rw "${TEST_DIR}" || true
    fi
fi

echo "Permission cleanup completed"
exit 0
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
    echo "Making files readable and writable for cleanup"
    
    # Try to make files readable/writable without changing ownership
    # This should be sufficient for Jenkins cleanup
    if chmod -R a+rw "${OBJ_DIR}" 2>/dev/null; then
        echo "Successfully updated permissions"
    else
        echo "Warning: Could not update all permissions, but continuing..."
    fi
    
    echo "Cleanup complete"
else
    echo "Object directory ${OBJ_DIR} not found, nothing to clean"
fi

# Also handle potential root-owned files in the tests directory
TEST_DIR="${WORKSPACE_ROOT}/simtemp/tests"
if [ -d "${TEST_DIR}" ]; then
    echo "Checking for permission issues in test directory"
    # Just ensure files are readable/writable, don't change ownership
    chmod -R a+rw "${TEST_DIR}" 2>/dev/null || {
        echo "Warning: Could not update all test directory permissions"
    }
fi

echo "Permission cleanup completed"
exit 0
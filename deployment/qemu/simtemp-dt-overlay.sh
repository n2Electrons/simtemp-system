#!/bin/bash

# SimTemp Device Tree Overlay Infrastructure Simulator
# Este script simula la infraestructura de DT overlay para testing F-K1-TC-002

SIMTEMP_QEMU_ROOT="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
MOCK_CONFIGFS_ROOT="/tmp/simtemp-mock-configfs"
MOCK_OVERLAY_DIR="${MOCK_CONFIGFS_ROOT}/device-tree/overlays"

setup_mock_dt_infrastructure() {
    echo "Setting up mock Device Tree overlay infrastructure..."
    
    # Crear estructura de directorio configfs mock
    mkdir -p "${MOCK_OVERLAY_DIR}"
    mkdir -p "${MOCK_CONFIGFS_ROOT}/device-tree"
    
    # Simular archivos de kernel que F-K1-TC-002 va a buscar
    echo "live" > "${MOCK_CONFIGFS_ROOT}/device-tree/overlays/.loading_method"
    echo "configfs" > "${MOCK_CONFIGFS_ROOT}/device-tree/overlays/.api_type"
    echo "enabled" > "${MOCK_CONFIGFS_ROOT}/device-tree/overlays/.status"
    
    # Crear overlay de prueba disponible
    mkdir -p "${MOCK_OVERLAY_DIR}/simtemp-test"
    echo "simtemp-test-overlay" > "${MOCK_OVERLAY_DIR}/simtemp-test/path"
    echo "applied" > "${MOCK_OVERLAY_DIR}/simtemp-test/status"
    
    # Simular procfs entries
    mkdir -p "/tmp/simtemp-mock-proc/device-tree"
    echo "overlay-support = \"true\";" > "/tmp/simtemp-mock-proc/device-tree/overlay"
    
    # Variable de entorno para que F-K1-TC-002 encuentre la infraestructura
    export SIMTEMP_DT_CONFIGFS_ROOT="${MOCK_CONFIGFS_ROOT}"
    export SIMTEMP_DT_PROC_ROOT="/tmp/simtemp-mock-proc"
    export SIMTEMP_DT_OVERLAY_SUPPORT="true"
    
    echo "Mock DT overlay infrastructure ready at: ${MOCK_CONFIGFS_ROOT}"
    echo "Use SIMTEMP_DT_CONFIGFS_ROOT environment variable in tests"
    return 0
}

cleanup_mock_dt_infrastructure() {
    echo "Cleaning up mock Device Tree overlay infrastructure..."
    rm -rf "${MOCK_CONFIGFS_ROOT}"
    rm -rf "/tmp/simtemp-mock-proc"
    unset SIMTEMP_DT_CONFIGFS_ROOT
    unset SIMTEMP_DT_PROC_ROOT
    unset SIMTEMP_DT_OVERLAY_SUPPORT
    echo "Mock infrastructure cleaned up"
}

install_overlay() {
    local overlay_name="$1"
    local overlay_file="${SIMTEMP_QEMU_ROOT}/overlay/${overlay_name}.dtbo"
    
    if [[ ! -f "${overlay_file}" ]]; then
        echo "Error: Overlay file not found: ${overlay_file}"
        return 1
    fi
    
    echo "Installing overlay: ${overlay_name}"
    mkdir -p "${MOCK_OVERLAY_DIR}/${overlay_name}"
    cp "${overlay_file}" "${MOCK_OVERLAY_DIR}/${overlay_name}/dtbo"
    echo "applied" > "${MOCK_OVERLAY_DIR}/${overlay_name}/status"
    echo "${overlay_file}" > "${MOCK_OVERLAY_DIR}/${overlay_name}/path"
    
    echo "Overlay ${overlay_name} installed successfully"
    return 0
}

remove_overlay() {
    local overlay_name="$1"
    
    if [[ -d "${MOCK_OVERLAY_DIR}/${overlay_name}" ]]; then
        echo "Removing overlay: ${overlay_name}"
        rm -rf "${MOCK_OVERLAY_DIR}/${overlay_name}"
        echo "Overlay ${overlay_name} removed successfully"
    else
        echo "Warning: Overlay ${overlay_name} not found"
        return 1
    fi
}

list_overlays() {
    echo "Available overlays in mock infrastructure:"
    if [[ -d "${MOCK_OVERLAY_DIR}" ]]; then
        ls -1 "${MOCK_OVERLAY_DIR}/" 2>/dev/null || echo "No overlays found"
    else
        echo "Mock infrastructure not initialized. Run 'setup' first."
    fi
}

run_f_k1_tc_002_test() {
    local dev_mode="$1"
    
    if [[ "${dev_mode}" == "--dev-mode" ]]; then
        echo "Running F-K1-TC-002 test in DEVELOPMENT MODE (with mock DT overlay infrastructure)..."
        echo "WARNING: This mode simulates DT overlay infrastructure for testing purposes only!"
        echo "In production, this test should FAIL without real DT overlay support."
        echo ""
        
        # Configurar infraestructura mock solo en modo desarrollo
        setup_mock_dt_infrastructure
        
        echo "Environment variables for development test:"
        echo "SIMTEMP_DT_CONFIGFS_ROOT=${SIMTEMP_DT_CONFIGFS_ROOT}"
        echo "SIMTEMP_DT_PROC_ROOT=${SIMTEMP_DT_PROC_ROOT}"
        echo "SIMTEMP_DT_OVERLAY_SUPPORT=${SIMTEMP_DT_OVERLAY_SUPPORT}"
        echo ""
    else
        echo "Running F-K1-TC-002 test in NORMAL MODE (no mock infrastructure)..."
        echo "This test SHOULD FAIL without real Device Tree overlay support."
        echo "This is the CORRECT behavior for this test."
        echo ""
    fi
    
    # Ejecutar el test
    cd "/home/jorge/challenge-2509/simtemp-system"
    
    # Ejecutar el test específico
    python3 -m pytest simtemp/tests/test_f_k1_tc_002.py::test_dt_overlay_driver_binding -v --tb=short
    
    local exit_code=$?
    
    if [[ "${dev_mode}" == "--dev-mode" ]]; then
        echo "F-K1-TC-002 DEVELOPMENT test completed with exit code: ${exit_code}"
        if [[ ${exit_code} -eq 0 ]]; then
            echo "✓ Test PASSED in dev mode - DT overlay detection logic works correctly"
        else
            echo "✗ Test FAILED in dev mode - check DT overlay detection logic"
        fi
        cleanup_mock_dt_infrastructure
    else
        echo "F-K1-TC-002 NORMAL test completed with exit code: ${exit_code}"
        if [[ ${exit_code} -ne 0 ]]; then
            echo "✓ Test FAILED as expected - no real DT overlay infrastructure found"
            echo "✓ This is the CORRECT behavior for F-K1-TC-002"
        else
            echo "⚠ WARNING: Test PASSED unexpectedly - this may indicate a problem"
            echo "⚠ F-K1-TC-002 should FAIL without real DT overlay support"
        fi
    fi
    
    return ${exit_code}
}

# Main script logic
case "${1}" in
    "setup")
        setup_mock_dt_infrastructure
        ;;
    "cleanup")
        cleanup_mock_dt_infrastructure
        ;;
    "install")
        if [[ -z "${2}" ]]; then
            echo "Usage: $0 install <overlay_name>"
            echo "Available overlays:"
            ls -1 "${SIMTEMP_QEMU_ROOT}/overlay/"*.dts 2>/dev/null | sed 's/.*\///;s/\.dts$//' || echo "No overlay source files found"
            exit 1
        fi
        setup_mock_dt_infrastructure
        install_overlay "${2}"
        ;;
    "remove")
        if [[ -z "${2}" ]]; then
            echo "Usage: $0 remove <overlay_name>"
            exit 1
        fi
        remove_overlay "${2}"
        ;;
    "list")
        list_overlays
        ;;
    "test")
        run_f_k1_tc_002_test
        ;;
    "test-dev")
        run_f_k1_tc_002_test "--dev-mode"
        ;;
    *)
        echo "SimTemp Device Tree Overlay Infrastructure Simulator"
        echo ""
        echo "Usage: $0 {setup|cleanup|install|remove|list|test|test-dev}"
        echo ""
        echo "Commands:"
        echo "  setup              - Set up mock DT overlay infrastructure"
        echo "  cleanup            - Clean up mock infrastructure"
        echo "  install <overlay>  - Install a specific overlay"
        echo "  remove <overlay>   - Remove a specific overlay"
        echo "  list               - List currently installed overlays"
        echo "  test               - Run F-K1-TC-002 test in NORMAL mode (should FAIL)"
        echo "  test-dev           - Run F-K1-TC-002 test in DEVELOPMENT mode (with mock)"
        echo ""
        echo "IMPORTANT:"
        echo "  - 'test' mode should FAIL - this is correct behavior!"
        echo "  - 'test-dev' mode is for verifying test logic only"
        echo "  - In production, F-K1-TC-002 should fail without real DT overlay"
        echo ""
        echo "Available overlays:"
        ls -1 "${SIMTEMP_QEMU_ROOT}/overlay/"*.dts 2>/dev/null | sed 's/.*\///;s/\.dts$//' || echo "No overlay source files found"
        exit 1
        ;;
esac
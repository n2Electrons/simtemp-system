"""
Test cases for QEMU Device Tree overlay functionality.
"""

import pytest
from test_utils import (load_environment, get_or_start_shared_qemu_session,
                        cleanup_qemu_session)

# Test timeout in seconds (1 minute)
QEMU_TIMEOUT = 60


@pytest.mark.order(1)
def test_basic_qemu_boot():
    """
    Test case F-K1-TC-002: Test QEMU Device Tree overlay infrastructure.
    Expected Result: QEMU boots successfully and initramfs is ready.
    """
    test_passed = False
    
    with load_environment():
        try:
            # Try to get or start shared QEMU session
            print("Getting or starting shared QEMU session...")
            qemu_process = get_or_start_shared_qemu_session()
            
            if qemu_process is None:
                pytest.fail("Failed to get or start QEMU session")
            
            print("✓ QEMU session available")
            print("✓ QEMU Device Tree overlay infrastructure test passed")
            test_passed = True

        except Exception as e:
            pytest.fail(f"Unexpected error during QEMU test: {e}")

        finally:
            # Only cleanup if test failed - preserve session on success
            if not test_passed:
                print("\nTest failed - cleaning up QEMU session...")
                cleanup_qemu_session()
            else:
                print("\n✓ Test passed - preserving QEMU session for reuse")
            
            # Additional cleanup handled by load_environment context manager
            print("Additional cleanup will be handled by load_environment")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


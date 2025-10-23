"""
Test case F-K1-TC-002: QEMU Boot Test
Boot on QEMU with no errors. Able to reuse QEMU session for further testing.
"""

import pytest
from test_utils import get_or_start_shared_qemu_session

# Test timeout in seconds (1 minute)
QEMU_TIMEOUT = 60


@pytest.mark.order(1)
def test_basic_qemu_boot():
    """
    Test case F-K1-TC-002: QEMU Boot Test
    Expected Result: Boot on QEMU with no errors. Able to reuse QEMU session for further testing.
    """
    try:
        # Try to get or start shared QEMU session
        print("Getting or starting shared QEMU session...")
        qemu_process = get_or_start_shared_qemu_session()
        
        if qemu_process is None:
            pytest.fail("Failed to get or start QEMU session")
        
        print("✓ QEMU session available")
        print("✓ QEMU boot test passed - ready for further testing")
        
        # Test passed - preserve QEMU session for other tests
        print("✓ Test passed - preserving QEMU session for reuse")

    except Exception as e:
        pytest.fail(f"Unexpected error during QEMU boot test: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


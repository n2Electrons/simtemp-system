"""
TestMode Module

Implements test mode functionality for the Challenge 2025 temperature sensor.
Test mode sets a low threshold and verifies that alert events occur within expected timeframe.
"""

import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TestMode:
    """Test mode implementation for temperature sensor validation."""
    
    def __init__(self, config, reader):
        """
        Initialize test mode.
        
        Args:
            config: SysfsConfig instance
            reader: SimtempReader instance
        """
        self.config = config
        self.reader = reader
        self.original_config = None
        
    def save_current_config(self) -> bool:
        """Save current configuration for restoration after test."""
        try:
            self.original_config = self.config.get_current_config()
            logger.info("Saved current configuration for test mode")
            return True
        except Exception as e:
            logger.error(f"Failed to save current configuration: {e}")
            return False
    
    def restore_original_config(self) -> bool:
        """Restore original configuration after test."""
        if self.original_config is None:
            logger.warning("No original configuration to restore")
            return True
        
        try:
            results = self.config.set_config(**self.original_config)
            success = all(results.values())
            
            if success:
                logger.info("Restored original configuration")
            else:
                logger.warning(f"Failed to restore some configuration values: {results}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to restore original configuration: {e}")
            return False
    
    def run_threshold_test(self, test_duration: float = 30.0) -> bool:
        """
        Run threshold crossing test.
        
        This test:
        1. Saves current configuration
        2. Sets a threshold that should trigger an alert
        3. Waits for alert within 2 sampling periods
        4. Restores original configuration
        
        Args:
            test_duration: Maximum test duration in seconds
            
        Returns:
            True if test passes, False if test fails
        """
        logger.info("Starting threshold crossing test...")
        
        # Save current configuration
        if not self.save_current_config():
            return False
        
        try:
            return self._execute_threshold_test(test_duration)
        finally:
            # Always try to restore original configuration
            self.restore_original_config()
    
    def _execute_threshold_test(self, test_duration: float) -> bool:
        """Execute the actual threshold test logic."""
        
        # Step 1: Get current temperature to set appropriate threshold
        logger.info("Reading current temperature...")
        current_sample = self._get_current_temperature()
        if current_sample is None:
            logger.error("Failed to read current temperature")
            return False
        
        current_temp_mc = current_sample['temp_mC']
        logger.info(f"Current temperature: {current_temp_mc/1000:.2f}°C")
        
        # Step 2: Set test configuration
        test_config = self._calculate_test_config(current_temp_mc)
        if not self._apply_test_config(test_config):
            return False
        
        # Step 3: Wait for threshold crossing
        logger.info(f"Waiting for threshold crossing (max {test_duration} seconds)...")
        return self._wait_for_threshold_crossing(test_duration, test_config)
    
    def _get_current_temperature(self, max_attempts: int = 5) -> Optional[Dict]:
        """Get current temperature sample."""
        for attempt in range(max_attempts):
            try:
                sample = self.reader.read_sample(timeout_ms=2000)
                if sample is not None:
                    return sample
                else:
                    logger.warning(f"No sample received on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Failed to read sample on attempt {attempt + 1}: {e}")
        
        return None
    
    def _calculate_test_config(self, current_temp_mc: int) -> Dict[str, Any]:
        """
        Calculate test configuration based on current temperature.
        
        Strategy:
        - Set threshold slightly below current temperature to trigger alerts
        - Use fast sampling for quick test completion
        """
        # Set threshold 0.5°C below current temperature
        test_threshold_mc = current_temp_mc - 500  # 0.5°C in milli-degrees
        
        # Use fast sampling for quicker test
        test_sampling_ms = 50  # 50ms = 20 samples/second
        
        # Use normal mode for predictable behavior
        test_mode = 'normal'
        
        config = {
            'threshold_mC': test_threshold_mc,
            'sampling_ms': test_sampling_ms,
            'mode': test_mode
        }
        
        logger.info(f"Test configuration: threshold={test_threshold_mc/1000:.2f}°C, "
                   f"sampling={test_sampling_ms}ms, mode={test_mode}")
        
        return config
    
    def _apply_test_config(self, test_config: Dict[str, Any]) -> bool:
        """Apply test configuration to sensor."""
        try:
            results = self.config.set_config(**test_config)
            success = all(results.values())
            
            if success:
                logger.info("Applied test configuration successfully")
                
                # Verify configuration was applied
                time.sleep(0.1)  # Small delay for configuration to take effect
                current = self.config.get_current_config()
                
                for key, expected in test_config.items():
                    actual = current.get(key)
                    if actual != expected:
                        logger.warning(f"Configuration mismatch for {key}: "
                                     f"expected {expected}, got {actual}")
                
            else:
                logger.error(f"Failed to apply test configuration: {results}")
            
            return success
            
        except Exception as e:
            logger.error(f"Exception applying test configuration: {e}")
            return False
    
    def _wait_for_threshold_crossing(self, max_duration: float, test_config: Dict) -> bool:
        """
        Wait for threshold crossing event.
        
        The test passes if we receive a sample with threshold_crossed flag
        within the specified duration.
        """
        start_time = time.time()
        sampling_period_sec = test_config['sampling_ms'] / 1000.0
        max_wait_periods = 2  # Wait maximum 2 sampling periods for crossing
        max_wait_time = min(max_duration, max_wait_periods * sampling_period_sec)
        
        logger.info(f"Waiting up to {max_wait_time:.1f} seconds for threshold crossing...")
        
        samples_received = 0
        threshold_crossed_samples = 0
        
        while (time.time() - start_time) < max_wait_time:
            try:
                # Read sample with timeout
                timeout_ms = int(sampling_period_sec * 1000 * 1.5)  # 1.5x sampling period
                sample = self.reader.read_sample(timeout_ms=timeout_ms)
                
                if sample is not None:
                    samples_received += 1
                    temp_c = sample['temp_mC'] / 1000.0
                    threshold_crossed = sample.get('threshold_crossed', False)
                    
                    logger.debug(f"Sample {samples_received}: {temp_c:.2f}°C, "
                               f"crossed={threshold_crossed}")
                    
                    if threshold_crossed:
                        threshold_crossed_samples += 1
                        logger.info(f"Threshold crossing detected! Temperature: {temp_c:.2f}°C")
                        
                        # Verify this is a legitimate crossing
                        if self._verify_threshold_crossing(sample, test_config):
                            logger.info("TEST PASSED: Valid threshold crossing detected")
                            return True
                    
                else:
                    logger.warning("Timeout waiting for sample")
            
            except Exception as e:
                logger.error(f"Error reading sample during test: {e}")
        
        # Test failed - log diagnostic information
        elapsed = time.time() - start_time
        logger.error(f"TEST FAILED: No valid threshold crossing detected in {elapsed:.1f} seconds")
        logger.error(f"Samples received: {samples_received}")
        logger.error(f"Threshold crossed samples: {threshold_crossed_samples}")
        
        return False
    
    def _verify_threshold_crossing(self, sample: Dict, test_config: Dict) -> bool:
        """
        Verify that a threshold crossing is legitimate.
        
        This checks that:
        1. The threshold_crossed flag is set
        2. The temperature is reasonably close to the configured threshold
        """
        threshold_crossed = sample.get('threshold_crossed', False)
        if not threshold_crossed:
            return False
        
        temp_mc = sample['temp_mC']
        configured_threshold_mc = test_config['threshold_mC']
        
        # Allow some tolerance (±1°C) for threshold crossing
        tolerance_mc = 1000  # 1°C in milli-degrees
        temp_diff = abs(temp_mc - configured_threshold_mc)
        
        if temp_diff <= tolerance_mc:
            logger.debug(f"Valid threshold crossing: temp={temp_mc/1000:.2f}°C, "
                        f"threshold={configured_threshold_mc/1000:.2f}°C, "
                        f"diff={temp_diff/1000:.2f}°C")
            return True
        else:
            logger.warning(f"Suspicious threshold crossing: temp={temp_mc/1000:.2f}°C, "
                          f"threshold={configured_threshold_mc/1000:.2f}°C, "
                          f"diff={temp_diff/1000:.2f}°C (tolerance={tolerance_mc/1000:.2f}°C)")
            return False
    
    def run_sampling_test(self, expected_period_ms: int, test_duration: float = 10.0) -> bool:
        """
        Test sampling period accuracy.
        
        Args:
            expected_period_ms: Expected sampling period in milliseconds
            test_duration: Test duration in seconds
            
        Returns:
            True if sampling is within acceptable tolerance
        """
        logger.info(f"Starting sampling period test (expected: {expected_period_ms}ms)...")
        
        if not self.save_current_config():
            return False
        
        try:
            # Set test sampling period
            if not self.config.set_sampling_period(expected_period_ms):
                logger.error("Failed to set test sampling period")
                return False
            
            # Collect samples
            samples = []
            start_time = time.time()
            
            while (time.time() - start_time) < test_duration:
                sample = self.reader.read_sample(timeout_ms=expected_period_ms * 3)
                if sample:
                    samples.append(sample['timestamp_ns'])
            
            # Analyze timing
            if len(samples) < 2:
                logger.error("Insufficient samples for timing analysis")
                return False
            
            # Calculate actual periods
            periods_ns = [samples[i] - samples[i-1] for i in range(1, len(samples))]
            periods_ms = [p / 1e6 for p in periods_ns]  # Convert to milliseconds
            
            avg_period = sum(periods_ms) / len(periods_ms)
            tolerance = expected_period_ms * 0.1  # 10% tolerance
            
            logger.info(f"Expected period: {expected_period_ms}ms")
            logger.info(f"Actual average period: {avg_period:.2f}ms")
            logger.info(f"Tolerance: ±{tolerance:.2f}ms")
            
            if abs(avg_period - expected_period_ms) <= tolerance:
                logger.info("TEST PASSED: Sampling period within tolerance")
                return True
            else:
                logger.error("TEST FAILED: Sampling period outside tolerance")
                return False
        
        finally:
            self.restore_original_config()
    
    def run_comprehensive_test(self) -> Dict[str, bool]:
        """
        Run comprehensive test suite.
        
        Returns:
            Dictionary with results for each test
        """
        results = {}
        
        logger.info("Starting comprehensive test suite...")
        
        # Test 1: Threshold crossing
        results['threshold_crossing'] = self.run_threshold_test()
        
        # Test 2: Sampling period accuracy
        results['sampling_accuracy'] = self.run_sampling_test(100)  # 100ms test
        
        # Test 3: Configuration persistence
        results['config_persistence'] = self._test_config_persistence()
        
        # Summary
        passed_tests = sum(results.values())
        total_tests = len(results)
        
        logger.info(f"Comprehensive test results: {passed_tests}/{total_tests} tests passed")
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"  {test_name}: {status}")
        
        return results
    
    def _test_config_persistence(self) -> bool:
        """Test that configuration changes persist correctly."""
        logger.info("Testing configuration persistence...")
        
        test_values = {
            'sampling_ms': 200,
            'threshold_mC': 35000,
            'mode': 'noisy'
        }
        
        try:
            # Set test values
            results = self.config.set_config(**test_values)
            if not all(results.values()):
                logger.error("Failed to set test configuration")
                return False
            
            # Read back and verify
            time.sleep(0.1)  # Small delay
            current = self.config.get_current_config()
            
            for key, expected in test_values.items():
                actual = current.get(key)
                if actual != expected:
                    logger.error(f"Configuration persistence failed for {key}: "
                               f"expected {expected}, got {actual}")
                    return False
            
            logger.info("Configuration persistence test passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration persistence test error: {e}")
            return False


def run_quick_test(config, reader) -> bool:
    """
    Run a quick validation test.
    
    Args:
        config: SysfsConfig instance
        reader: SimtempReader instance
        
    Returns:
        True if basic functionality works
    """
    test = TestMode(config, reader)
    return test.run_threshold_test(test_duration=15.0)


if __name__ == "__main__":
    # Test mode can't run standalone - needs config and reader instances
    logging.basicConfig(level=logging.INFO)
    print("TestMode module - use with SysfsConfig and SimtempReader instances")
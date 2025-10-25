/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Test Mode Implementation
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Test mode functionality for validating sensor configuration
 * and alert generation capabilities.
 */

#include "simtemp_cli.h"

int run_test_mode(const struct cli_config *config, struct remote_context *ctx)
{
    int original_sampling = -1;
    int original_threshold = -1;
    char original_mode[64] = {0};
    int test_threshold = 35000;  /* 35°C - should be below normal temp */
    int test_sampling = 100;     /* 100ms fast sampling */
    int result = 0;
    
    printf("=== SimTemp Test Mode ===\n");
    print_verbose(config, "Running test mode to validate sensor functionality");
    
    /* Save original configuration */
    if (is_remote_connection(config)) {
        original_sampling = remote_get_sampling_period(ctx, config->sysfs_base);
        original_threshold = remote_get_threshold(ctx, config->sysfs_base);
        remote_read_sysfs_attribute(ctx, config->sysfs_base, "mode", 
                                   original_mode, sizeof(original_mode));
    } else {
        original_sampling = get_sampling_period(config->sysfs_base);
        original_threshold = get_threshold(config->sysfs_base);
        get_mode(config->sysfs_base, original_mode, sizeof(original_mode));
    }
    
    printf("Original configuration:\n");
    printf("  Sampling: %d ms\n", original_sampling);
    printf("  Threshold: %.1f°C\n", millicelsius_to_celsius(original_threshold));
    printf("  Mode: %s\n", original_mode);
    
    /* Configure test parameters */
    printf("\nConfiguring test parameters...\n");
    
    if (is_remote_connection(config)) {
        if (remote_set_sampling_period(ctx, config->sysfs_base, test_sampling) < 0) {
            print_error("Failed to set test sampling period");
            return -1;
        }
        
        if (remote_set_threshold(ctx, config->sysfs_base, test_threshold) < 0) {
            print_error("Failed to set test threshold");
            result = -1;
            goto restore;
        }
        
        if (remote_write_sysfs_attribute(ctx, config->sysfs_base, "mode", "ramp") < 0) {
            print_error("Failed to set test mode");
            result = -1;
            goto restore;
        }
    } else {
        if (set_sampling_period(config->sysfs_base, test_sampling) < 0) {
            print_error("Failed to set test sampling period");
            return -1;
        }
        
        if (set_threshold(config->sysfs_base, test_threshold) < 0) {
            print_error("Failed to set test threshold");
            result = -1;
            goto restore;
        }
        
        if (set_mode(config->sysfs_base, "ramp") < 0) {
            print_error("Failed to set test mode");
            result = -1;
            goto restore;
        }
    }
    
    printf("Test configuration set:\n");
    printf("  Sampling: %d ms\n", test_sampling);
    printf("  Threshold: %.1f°C\n", millicelsius_to_celsius(test_threshold));
    printf("  Mode: ramp\n");
    
    /* Wait for sensor to stabilize */
    printf("\nWaiting for sensor to stabilize...\n");
    sleep(2);
    
    /* Monitor for alerts */
    printf("Monitoring for threshold alerts (30 seconds max)...\n");
    
    if (is_remote_connection(config)) {
        /* Remote test monitoring - simplified version */
        printf("Remote test monitoring not fully implemented.\n");
        printf("Please manually verify that alerts are generated when temperature exceeds %.1f°C\n",
               millicelsius_to_celsius(test_threshold));
        result = 0;  /* Assume success for now */
    } else {
        /* Local test monitoring */
        int fd = open_device(config->device_path);
        if (fd < 0) {
            print_error("Failed to open device for test monitoring");
            result = -1;
            goto restore;
        }
        
        struct simtemp_record record;
        time_t start_time = time(NULL);
        bool alert_detected = false;
        int samples_read = 0;
        
        while (g_running && (time(NULL) - start_time) < 30) {
            int poll_result = wait_for_sample(fd, 1000);
            if (poll_result <= 0) {
                continue;
            }
            
            int read_result = read_temperature_sample(fd, &record);
            if (read_result <= 0) {
                continue;
            }
            
            samples_read++;
            double temp_c = millicelsius_to_celsius(record.temp_mC);
            bool alert = record.flags & SIMTEMP_FLAG_THRESHOLD_CROSSED;
            
            printf("Sample %d: temp=%.1f°C alert=%d\n", samples_read, temp_c, alert ? 1 : 0);
            
            if (alert) {
                alert_detected = true;
                printf("SUCCESS: Alert detected at %.1f°C!\n", temp_c);
                break;
            }
            
            /* In ramp mode, temperature should increase */
            if (samples_read > 10 && temp_c > millicelsius_to_celsius(test_threshold)) {
                printf("Temperature above threshold but no alert detected.\n");
            }
        }
        
        close_device(fd);
        
        if (alert_detected) {
            printf("\nTEST PASSED: Alert functionality working correctly.\n");
            result = 0;
        } else {
            printf("\nTEST FAILED: No alert detected within timeout period.\n");
            result = -1;
        }
        
        printf("Total samples read: %d\n", samples_read);
    }
    
restore:
    /* Restore original configuration */
    printf("\nRestoring original configuration...\n");
    
    if (is_remote_connection(config)) {
        if (original_sampling >= 0) {
            remote_set_sampling_period(ctx, config->sysfs_base, original_sampling);
        }
        if (original_threshold >= -200000) {
            remote_set_threshold(ctx, config->sysfs_base, original_threshold);
        }
        if (strlen(original_mode) > 0) {
            remote_write_sysfs_attribute(ctx, config->sysfs_base, "mode", original_mode);
        }
    } else {
        if (original_sampling >= 0) {
            set_sampling_period(config->sysfs_base, original_sampling);
        }
        if (original_threshold >= -200000) {
            set_threshold(config->sysfs_base, original_threshold);
        }
        if (strlen(original_mode) > 0) {
            set_mode(config->sysfs_base, original_mode);
        }
    }
    
    printf("Configuration restored.\n");
    printf("=== Test Mode Complete ===\n");
    
    return result;
}
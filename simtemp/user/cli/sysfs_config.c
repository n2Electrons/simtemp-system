/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Sysfs Configuration
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Sysfs attribute access functions for configuring the SimTemp
 * temperature sensor driver parameters.
 */

#include "simtemp_cli.h"

int read_sysfs_attribute(const char *base_path, const char *attr_name, 
                        char *value, size_t value_size)
{
    char path[512];
    FILE *file;
    char *newline;
    
    /* Build full attribute path */
    snprintf(path, sizeof(path), "%s/%s", base_path, attr_name);
    
    /* Open attribute file */
    file = fopen(path, "r");
    if (!file) {
        print_error("Failed to open sysfs attribute %s: %s", path, strerror(errno));
        return -1;
    }
    
    /* Read value */
    if (!fgets(value, value_size, file)) {
        print_error("Failed to read sysfs attribute %s: %s", path, strerror(errno));
        fclose(file);
        return -1;
    }
    
    fclose(file);
    
    /* Remove trailing newline */
    newline = strchr(value, '\n');
    if (newline) {
        *newline = '\0';
    }
    
    return 0;
}

int write_sysfs_attribute(const char *base_path, const char *attr_name, 
                         const char *value)
{
    char path[512];
    FILE *file;
    
    /* Build full attribute path */
    snprintf(path, sizeof(path), "%s/%s", base_path, attr_name);
    
    /* Open attribute file for writing */
    file = fopen(path, "w");
    if (!file) {
        print_error("Failed to open sysfs attribute %s for writing: %s", 
                   path, strerror(errno));
        return -1;
    }
    
    /* Write value */
    if (fprintf(file, "%s", value) < 0) {
        print_error("Failed to write sysfs attribute %s: %s", path, strerror(errno));
        fclose(file);
        return -1;
    }
    
    fclose(file);
    
    return 0;
}

int get_sampling_period(const char *sysfs_base)
{
    char value[64];
    
    if (read_sysfs_attribute(sysfs_base, "sampling_ms", value, sizeof(value)) < 0) {
        return -1;
    }
    
    return atoi(value);
}

int set_sampling_period(const char *sysfs_base, int period_ms)
{
    char value[64];
    
    if (!validate_sampling_period(period_ms)) {
        print_error("Invalid sampling period: %d ms (valid range: 1-60000)", period_ms);
        return -1;
    }
    
    snprintf(value, sizeof(value), "%d", period_ms);
    
    return write_sysfs_attribute(sysfs_base, "sampling_ms", value);
}

int get_threshold(const char *sysfs_base)
{
    char value[64];
    
    if (read_sysfs_attribute(sysfs_base, "threshold_mC", value, sizeof(value)) < 0) {
        return -1;
    }
    
    return atoi(value);
}

int set_threshold(const char *sysfs_base, int threshold_mc)
{
    char value[64];
    
    if (!validate_threshold(threshold_mc)) {
        print_error("Invalid threshold: %d mC (valid range: -50000-150000)", threshold_mc);
        return -1;
    }
    
    snprintf(value, sizeof(value), "%d", threshold_mc);
    
    return write_sysfs_attribute(sysfs_base, "threshold_mC", value);
}

int get_mode(const char *sysfs_base, char *mode, size_t mode_size)
{
    return read_sysfs_attribute(sysfs_base, "mode", mode, mode_size);
}

int set_mode(const char *sysfs_base, const char *mode)
{
    if (!validate_mode(mode)) {
        print_error("Invalid mode: %s (valid modes: normal, noisy, ramp, static, linear)", mode);
        return -1;
    }
    
    return write_sysfs_attribute(sysfs_base, "mode", mode);
}

int configure_sensor(const struct cli_config *config, struct remote_context *ctx)
{
    int result = 0;
    bool any_config = false;
    
    if (is_remote_connection(config)) {
        /* Remote configuration */
        print_verbose(config, "Configuring remote sensor via %s", 
                     get_connection_type_string(config->conn_type));
        
        if (config->sampling_ms > 0) {
            if (remote_set_sampling_period(ctx, config->sysfs_base, config->sampling_ms) < 0) {
                print_error("Failed to set remote sampling period");
                result = -1;
            } else {
                printf("Set remote sampling period to %d ms\n", config->sampling_ms);
                any_config = true;
            }
        }
        
        if (config->threshold_mc > 0) {
            if (remote_set_threshold(ctx, config->sysfs_base, config->threshold_mc) < 0) {
                print_error("Failed to set remote threshold");
                result = -1;
            } else {
                printf("Set remote threshold to %.1f°C\n", 
                       millicelsius_to_celsius(config->threshold_mc));
                any_config = true;
            }
        }
        
        if (strlen(config->mode) > 0 && strcmp(config->mode, "normal") != 0) {
            if (remote_write_sysfs_attribute(ctx, config->sysfs_base, "mode", config->mode) < 0) {
                print_error("Failed to set remote mode");
                result = -1;
            } else {
                printf("Set remote mode to %s\n", config->mode);
                any_config = true;
            }
        }
    } else {
        /* Local configuration */
        print_verbose(config, "Configuring local sensor");
        
        if (config->sampling_ms > 0) {
            if (set_sampling_period(config->sysfs_base, config->sampling_ms) < 0) {
                print_error("Failed to set sampling period");
                result = -1;
            } else {
                printf("Set sampling period to %d ms\n", config->sampling_ms);
                any_config = true;
            }
        }
        
        if (config->threshold_mc > 0) {
            if (set_threshold(config->sysfs_base, config->threshold_mc) < 0) {
                print_error("Failed to set threshold");
                result = -1;
            } else {
                printf("Set threshold to %.1f°C\n", 
                       millicelsius_to_celsius(config->threshold_mc));
                any_config = true;
            }
        }
        
        if (strlen(config->mode) > 0 && strcmp(config->mode, "normal") != 0) {
            if (set_mode(config->sysfs_base, config->mode) < 0) {
                print_error("Failed to set mode");
                result = -1;
            } else {
                printf("Set mode to %s\n", config->mode);
                any_config = true;
            }
        }
    }
    
    if (!any_config) {
        printf("No configuration parameters specified. Use --help for options.\n");
        return show_sensor_status(config, ctx);
    }
    
    return result;
}

int show_sensor_status(const struct cli_config *config, struct remote_context *ctx)
{
    int sampling_ms, threshold_mc;
    char mode[64];
    char stats[512];
    
    printf("\n=== SimTemp Sensor Status ===\n");
    printf("Connection: %s\n", get_connection_type_string(config->conn_type));
    
    if (is_remote_connection(config)) {
        printf("Remote host: %s:%d\n", config->remote_host, config->remote_port);
        printf("Username: %s\n", config->username);
    }
    
    printf("Device path: %s\n", config->device_path);
    printf("Sysfs path: %s\n", config->sysfs_base);
    
    /* Read current configuration */
    if (is_remote_connection(config)) {
        /* Remote status */
        sampling_ms = remote_get_sampling_period(ctx, config->sysfs_base);
        threshold_mc = remote_get_threshold(ctx, config->sysfs_base);
        
        if (remote_read_sysfs_attribute(ctx, config->sysfs_base, "mode", mode, sizeof(mode)) < 0) {
            strcpy(mode, "unknown");
        }
        
        if (remote_read_sysfs_attribute(ctx, config->sysfs_base, "stats", stats, sizeof(stats)) < 0) {
            strcpy(stats, "unavailable");
        }
    } else {
        /* Local status */
        sampling_ms = get_sampling_period(config->sysfs_base);
        threshold_mc = get_threshold(config->sysfs_base);
        
        if (get_mode(config->sysfs_base, mode, sizeof(mode)) < 0) {
            strcpy(mode, "unknown");
        }
        
        if (read_sysfs_attribute(config->sysfs_base, "stats", stats, sizeof(stats)) < 0) {
            strcpy(stats, "unavailable");
        }
    }
    
    printf("\n=== Configuration ===\n");
    if (sampling_ms >= 0) {
        printf("Sampling period: %d ms\n", sampling_ms);
    } else {
        printf("Sampling period: unavailable\n");
    }
    
    if (threshold_mc >= -200000) {  /* Check for reasonable value */
        printf("Threshold: %.1f°C (%d mC)\n", 
               millicelsius_to_celsius(threshold_mc), threshold_mc);
    } else {
        printf("Threshold: unavailable\n");
    }
    
    printf("Mode: %s\n", mode);
    
    printf("\n=== Statistics ===\n");
    if (strcmp(stats, "unavailable") != 0) {
        /* Parse and display stats */
        char *token = strtok(stats, ",");
        while (token) {
            char *colon = strchr(token, ':');
            if (colon) {
                *colon = '\0';
                printf("%s: %s\n", token, colon + 1);
            }
            token = strtok(NULL, ",");
        }
    } else {
        printf("Statistics unavailable\n");
    }
    
    printf("\n");
    
    return 0;
}
/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Device Operations
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Local device access functions for reading temperature samples
 * and managing device file operations.
 */

#include "simtemp_cli.h"

int open_device(const char *device_path)
{
    int fd = open(device_path, O_RDONLY);
    if (fd < 0) {
        print_error("Failed to open device %s: %s", device_path, strerror(errno));
        return -1;
    }
    
    return fd;
}

void close_device(int fd)
{
    if (fd >= 0) {
        close(fd);
    }
}

int wait_for_sample(int fd, int timeout_ms)
{
    struct pollfd pfd;
    int ret;
    
    pfd.fd = fd;
    pfd.events = POLLIN;
    pfd.revents = 0;
    
    ret = poll(&pfd, 1, timeout_ms);
    
    if (ret < 0) {
        print_error("Poll error: %s", strerror(errno));
        return -1;
    }
    
    if (ret == 0) {
        /* Timeout */
        return 0;
    }
    
    if (pfd.revents & POLLIN) {
        return 1;  /* Data available */
    }
    
    if (pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) {
        print_error("Poll error: device error/hangup/invalid");
        return -1;
    }
    
    return 0;
}

int read_temperature_sample(int fd, struct simtemp_record *record)
{
    ssize_t bytes_read;
    
    bytes_read = read(fd, record, sizeof(*record));
    
    if (bytes_read < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            /* No data available in non-blocking mode */
            return 0;
        }
        print_error("Failed to read temperature sample: %s", strerror(errno));
        return -1;
    }
    
    if (bytes_read == 0) {
        /* EOF - device closed */
        return -1;
    }
    
    if (bytes_read != sizeof(*record)) {
        print_error("Incomplete read: got %zd bytes, expected %zu bytes", 
                   bytes_read, sizeof(*record));
        return -1;
    }
    
    return 1;  /* Success */
}

int monitor_local_temperature(const struct cli_config *config)
{
    int fd = -1;
    struct simtemp_record record;
    time_t start_time, current_time;
    int samples_read = 0;
    int result = 0;
    
    /* Open device */
    fd = open_device(config->device_path);
    if (fd < 0) {
        return -1;
    }
    
    start_time = time(NULL);
    
    print_verbose(config, "Starting local temperature monitoring");
    print_verbose(config, "Device: %s", config->device_path);
    print_verbose(config, "Timeout: %d ms", config->poll_timeout_ms);
    
    while (g_running) {
        /* Check duration limit */
        if (config->duration_sec > 0) {
            current_time = time(NULL);
            if ((current_time - start_time) >= config->duration_sec) {
                print_verbose(config, "Duration limit reached");
                break;
            }
        }
        
        /* Check sample count limit */
        if (config->sample_count > 0 && samples_read >= config->sample_count) {
            print_verbose(config, "Sample count limit reached");
            break;
        }
        
        /* Wait for data to be available */
        int poll_result = wait_for_sample(fd, config->poll_timeout_ms);
        if (poll_result < 0) {
            print_error("Poll failed");
            result = -1;
            break;
        }
        
        if (poll_result == 0) {
            print_verbose(config, "Poll timeout, continuing...");
            continue;
        }
        
        /* Read temperature sample */
        int read_result = read_temperature_sample(fd, &record);
        if (read_result < 0) {
            print_error("Failed to read temperature sample");
            result = -1;
            break;
        }
        
        if (read_result == 0) {
            /* No data available, continue polling */
            continue;
        }
        
        /* Process and display the sample */
        print_temperature_sample(&record, config);
        update_stats(&g_stats, &record);
        samples_read++;
        
        /* Log alerts if verbose mode */
        if (config->verbose && (record.flags & SIMTEMP_FLAG_THRESHOLD_CROSSED)) {
            double temp_c = millicelsius_to_celsius(record.temp_mC);
            print_verbose(config, "ALERT: Temperature threshold crossed! %.1f°C", temp_c);
        }
    }
    
    close_device(fd);
    
    print_verbose(config, "Local monitoring completed. Samples read: %d", samples_read);
    
    return result;
}
/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Remote Operations
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Remote connection and command execution functions for SSH/Telnet
 * communication with remote SimTemp sensor devices.
 */

#include "simtemp_cli.h"

bool is_remote_connection(const struct cli_config *config)
{
    return (config->conn_type != CONNECTION_LOCAL && strlen(config->remote_host) > 0);
}

int build_ssh_command(const struct cli_config *config, const char *remote_cmd, 
                     char *full_cmd, size_t cmd_size)
{
    const char *ssh_opts = "-o ConnectTimeout=10 -o BatchMode=yes";
    
    if (strlen(config->keyfile) > 0) {
        snprintf(full_cmd, cmd_size, "ssh %s -i '%s' -p %d %s@%s '%s'",
                ssh_opts, config->keyfile, config->remote_port, 
                config->username, config->remote_host, remote_cmd);
    } else {
        snprintf(full_cmd, cmd_size, "ssh %s -p %d %s@%s '%s'",
                ssh_opts, config->remote_port,
                config->username, config->remote_host, remote_cmd);
    }
    
    return 0;
}

int build_telnet_command(const struct cli_config *config, const char *remote_cmd,
                        char *full_cmd, size_t cmd_size)
{
    /* For telnet, we'll use expect script or similar automation */
    snprintf(full_cmd, cmd_size, "echo '%s' | telnet %s %d",
            remote_cmd, config->remote_host, config->remote_port);
    
    return 0;
}

int connect_remote(struct remote_context *ctx, const struct cli_config *config)
{
    ctx->type = config->conn_type;
    ctx->port = config->remote_port;
    ctx->connected = false;
    
    strncpy(ctx->host, config->remote_host, sizeof(ctx->host) - 1);
    strncpy(ctx->user, config->username, sizeof(ctx->user) - 1);
    
    /* Test connection with a simple command */
    char test_cmd[1024];
    char output[256];
    
    if (config->conn_type == CONNECTION_SSH) {
        build_ssh_command(config, "echo 'connection_test'", test_cmd, sizeof(test_cmd));
    } else if (config->conn_type == CONNECTION_TELNET) {
        build_telnet_command(config, "echo 'connection_test'", test_cmd, sizeof(test_cmd));
    } else {
        print_error("Unsupported connection type");
        return -1;
    }
    
    FILE *pipe = popen(test_cmd, "r");
    if (!pipe) {
        print_error("Failed to create connection pipe: %s", strerror(errno));
        return -1;
    }
    
    if (fgets(output, sizeof(output), pipe) == NULL) {
        pclose(pipe);
        print_error("Connection test failed - no response");
        return -1;
    }
    
    int exit_code = pclose(pipe);
    if (exit_code != 0) {
        print_error("Connection test failed with exit code %d", exit_code);
        return -1;
    }
    
    /* Check if we got expected response */
    if (strstr(output, "connection_test") == NULL) {
        print_error("Connection test failed - unexpected response: %s", output);
        return -1;
    }
    
    ctx->connected = true;
    return 0;
}

void disconnect_remote(struct remote_context *ctx)
{
    if (ctx->cmd_pipe) {
        pclose(ctx->cmd_pipe);
        ctx->cmd_pipe = NULL;
    }
    
    ctx->connected = false;
}

int execute_remote_command(struct remote_context *ctx, const char *command, 
                          char *output, size_t output_size)
{
    FILE *pipe;
    size_t bytes_read = 0;
    
    pipe = popen(command, "r");
    if (!pipe) {
        print_error("Failed to execute remote command: %s", strerror(errno));
        return -1;
    }
    
    /* Read output */
    if (output && output_size > 0) {
        char *ptr = output;
        size_t remaining = output_size - 1;
        
        while (remaining > 0 && fgets(ptr, remaining, pipe)) {
            size_t len = strlen(ptr);
            ptr += len;
            remaining -= len;
            bytes_read += len;
        }
        
        *ptr = '\0';
        
        /* Remove trailing newline */
        if (bytes_read > 0 && output[bytes_read - 1] == '\n') {
            output[bytes_read - 1] = '\0';
        }
    }
    
    int exit_code = pclose(pipe);
    if (exit_code != 0) {
        print_error("Remote command failed with exit code %d", exit_code);
        return -1;
    }
    
    return 0;
}

int remote_read_sysfs_attribute(struct remote_context *ctx, const char *base_path,
                               const char *attr_name, char *value, size_t value_size)
{
    char remote_cmd[512];
    char full_cmd[1024];
    
    /* Build remote command to read sysfs attribute */
    snprintf(remote_cmd, sizeof(remote_cmd), "cat %s/%s 2>/dev/null", base_path, attr_name);
    
    /* Build SSH/telnet command */
    if (ctx->type == CONNECTION_SSH) {
        snprintf(full_cmd, sizeof(full_cmd), "ssh -o ConnectTimeout=5 -p %d %s@%s '%s'",
                ctx->port, ctx->user, ctx->host, remote_cmd);
    } else {
        print_error("Telnet not fully implemented for sysfs operations");
        return -1;
    }
    
    return execute_remote_command(ctx, full_cmd, value, value_size);
}

int remote_write_sysfs_attribute(struct remote_context *ctx, const char *base_path,
                                const char *attr_name, const char *value)
{
    char remote_cmd[512];
    char full_cmd[1024];
    
    /* Build remote command to write sysfs attribute */
    snprintf(remote_cmd, sizeof(remote_cmd), "echo '%s' > %s/%s 2>/dev/null", 
            value, base_path, attr_name);
    
    /* Build SSH/telnet command */
    if (ctx->type == CONNECTION_SSH) {
        snprintf(full_cmd, sizeof(full_cmd), "ssh -o ConnectTimeout=5 -p %d %s@%s '%s'",
                ctx->port, ctx->user, ctx->host, remote_cmd);
    } else {
        print_error("Telnet not fully implemented for sysfs operations");
        return -1;
    }
    
    return execute_remote_command(ctx, full_cmd, NULL, 0);
}

int remote_get_sampling_period(struct remote_context *ctx, const char *sysfs_base)
{
    char value[64];
    
    if (remote_read_sysfs_attribute(ctx, sysfs_base, "sampling_ms", value, sizeof(value)) < 0) {
        return -1;
    }
    
    return atoi(value);
}

int remote_set_sampling_period(struct remote_context *ctx, const char *sysfs_base, int period_ms)
{
    char value[64];
    
    if (!validate_sampling_period(period_ms)) {
        print_error("Invalid sampling period: %d ms", period_ms);
        return -1;
    }
    
    snprintf(value, sizeof(value), "%d", period_ms);
    
    return remote_write_sysfs_attribute(ctx, sysfs_base, "sampling_ms", value);
}

int remote_get_threshold(struct remote_context *ctx, const char *sysfs_base)
{
    char value[64];
    
    if (remote_read_sysfs_attribute(ctx, sysfs_base, "threshold_mC", value, sizeof(value)) < 0) {
        return -1;
    }
    
    return atoi(value);
}

int remote_set_threshold(struct remote_context *ctx, const char *sysfs_base, int threshold_mc)
{
    char value[64];
    
    if (!validate_threshold(threshold_mc)) {
        print_error("Invalid threshold: %d mC", threshold_mc);
        return -1;
    }
    
    snprintf(value, sizeof(value), "%d", threshold_mc);
    
    return remote_write_sysfs_attribute(ctx, sysfs_base, "threshold_mC", value);
}

int monitor_remote_temperature(const struct cli_config *config, struct remote_context *ctx)
{
    char remote_cmd[512];
    char full_cmd[1024];
    FILE *pipe;
    char line[1024];
    time_t start_time, current_time;
    int samples_read = 0;
    
    /* Build remote monitoring command */
    if (config->duration_sec > 0 && config->sample_count > 0) {
        snprintf(remote_cmd, sizeof(remote_cmd), 
                "timeout %d dd if=%s bs=20 count=%d 2>/dev/null | hexdump -C",
                config->duration_sec, config->device_path, config->sample_count);
    } else if (config->duration_sec > 0) {
        snprintf(remote_cmd, sizeof(remote_cmd), 
                "timeout %d dd if=%s bs=20 2>/dev/null | hexdump -C",
                config->duration_sec, config->device_path);
    } else if (config->sample_count > 0) {
        snprintf(remote_cmd, sizeof(remote_cmd), 
                "dd if=%s bs=20 count=%d 2>/dev/null | hexdump -C",
                config->device_path, config->sample_count);
    } else {
        snprintf(remote_cmd, sizeof(remote_cmd), 
                "dd if=%s bs=20 2>/dev/null | hexdump -C",
                config->device_path);
    }
    
    /* Build SSH command */
    if (ctx->type == CONNECTION_SSH) {
        snprintf(full_cmd, sizeof(full_cmd), "ssh -p %d %s@%s '%s'",
                ctx->port, ctx->user, ctx->host, remote_cmd);
    } else {
        print_error("Telnet monitoring not implemented");
        return -1;
    }
    
    print_verbose(config, "Starting remote monitoring with command: %s", remote_cmd);
    
    /* Execute command and read output */
    pipe = popen(full_cmd, "r");
    if (!pipe) {
        print_error("Failed to start remote monitoring: %s", strerror(errno));
        return -1;
    }
    
    start_time = time(NULL);
    
    while (g_running && fgets(line, sizeof(line), pipe)) {
        /* Parse hexdump output to extract temperature records */
        /* This is a simplified approach - in production, you'd want */
        /* a more robust binary data parsing mechanism */
        
        /* For now, just display the raw hexdump for debugging */
        if (config->raw_output) {
            printf("%s", line);
        }
        
        samples_read++;
        
        /* Check limits */
        current_time = time(NULL);
        if (config->duration_sec > 0 && (current_time - start_time) >= config->duration_sec) {
            break;
        }
        if (config->sample_count > 0 && samples_read >= config->sample_count) {
            break;
        }
    }
    
    pclose(pipe);
    
    print_verbose(config, "Remote monitoring completed. Lines read: %d", samples_read);
    
    return 0;
}

int monitor_temperature(const struct cli_config *config, struct remote_context *ctx)
{
    if (is_remote_connection(config)) {
        return monitor_remote_temperature(config, ctx);
    } else {
        return monitor_local_temperature(config);
    }
}
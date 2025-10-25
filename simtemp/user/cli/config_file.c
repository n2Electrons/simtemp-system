/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Configuration File Support
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Configuration file parsing and saving functionality
 * for persistent CLI settings.
 */

#include "simtemp_cli.h"

#define MAX_LINE_LENGTH 256
#define MAX_KEY_LENGTH 64
#define MAX_VALUE_LENGTH 192

static int parse_config_line(const char *line, char *key, char *value)
{
    const char *ptr = line;
    char *key_ptr = key;
    char *value_ptr = value;
    
    /* Skip whitespace */
    while (*ptr && (*ptr == ' ' || *ptr == '\t')) {
        ptr++;
    }
    
    /* Skip comments and empty lines */
    if (*ptr == '#' || *ptr == '\n' || *ptr == '\0') {
        return 0;
    }
    
    /* Read key */
    while (*ptr && *ptr != '=' && *ptr != ' ' && *ptr != '\t' && 
           (key_ptr - key) < (MAX_KEY_LENGTH - 1)) {
        *key_ptr++ = *ptr++;
    }
    *key_ptr = '\0';
    
    /* Skip whitespace and equals sign */
    while (*ptr && (*ptr == ' ' || *ptr == '\t' || *ptr == '=')) {
        ptr++;
    }
    
    /* Read value */
    while (*ptr && *ptr != '\n' && *ptr != '#' && 
           (value_ptr - value) < (MAX_VALUE_LENGTH - 1)) {
        *value_ptr++ = *ptr++;
    }
    *value_ptr = '\0';
    
    /* Trim trailing whitespace from value */
    value_ptr--;
    while (value_ptr >= value && (*value_ptr == ' ' || *value_ptr == '\t')) {
        *value_ptr-- = '\0';
    }
    
    return (strlen(key) > 0) ? 1 : 0;
}

int load_config_file(const char *filename, struct cli_config *config)
{
    FILE *file;
    char line[MAX_LINE_LENGTH];
    char key[MAX_KEY_LENGTH];
    char value[MAX_VALUE_LENGTH];
    int line_num = 0;
    
    file = fopen(filename, "r");
    if (!file) {
        print_error("Failed to open config file %s: %s", filename, strerror(errno));
        return -1;
    }
    
    printf("Loading configuration from %s\n", filename);
    
    while (fgets(line, sizeof(line), file)) {
        line_num++;
        
        if (!parse_config_line(line, key, value)) {
            continue;
        }
        
        /* Parse configuration options */
        if (strcmp(key, "remote_host") == 0) {
            strncpy(config->remote_host, value, sizeof(config->remote_host) - 1);
            config->conn_type = CONNECTION_SSH;
        } else if (strcmp(key, "remote_port") == 0) {
            config->remote_port = atoi(value);
        } else if (strcmp(key, "username") == 0) {
            strncpy(config->username, value, sizeof(config->username) - 1);
        } else if (strcmp(key, "keyfile") == 0) {
            strncpy(config->keyfile, value, sizeof(config->keyfile) - 1);
        } else if (strcmp(key, "connection_type") == 0) {
            if (strcmp(value, "ssh") == 0) {
                config->conn_type = CONNECTION_SSH;
            } else if (strcmp(value, "telnet") == 0) {
                config->conn_type = CONNECTION_TELNET;
            } else if (strcmp(value, "local") == 0) {
                config->conn_type = CONNECTION_LOCAL;
            }
        } else if (strcmp(key, "device_path") == 0) {
            strncpy(config->device_path, value, sizeof(config->device_path) - 1);
        } else if (strcmp(key, "sysfs_base") == 0) {
            strncpy(config->sysfs_base, value, sizeof(config->sysfs_base) - 1);
        } else if (strcmp(key, "sampling_ms") == 0) {
            config->sampling_ms = atoi(value);
        } else if (strcmp(key, "threshold_mc") == 0) {
            config->threshold_mc = atoi(value);
        } else if (strcmp(key, "mode") == 0) {
            strncpy(config->mode, value, sizeof(config->mode) - 1);
        } else if (strcmp(key, "poll_timeout_ms") == 0) {
            config->poll_timeout_ms = atoi(value);
        } else if (strcmp(key, "verbose") == 0) {
            config->verbose = (strcmp(value, "true") == 0 || strcmp(value, "1") == 0);
        } else if (strcmp(key, "json_output") == 0) {
            config->json_output = (strcmp(value, "true") == 0 || strcmp(value, "1") == 0);
        } else if (strcmp(key, "csv_output") == 0) {
            config->csv_output = (strcmp(value, "true") == 0 || strcmp(value, "1") == 0);
        } else {
            printf("Warning: Unknown configuration key '%s' on line %d\n", key, line_num);
        }
    }
    
    fclose(file);
    
    printf("Configuration loaded successfully\n");
    return 0;
}

int save_config_file(const char *filename, const struct cli_config *config)
{
    FILE *file;
    time_t now;
    
    file = fopen(filename, "w");
    if (!file) {
        print_error("Failed to create config file %s: %s", filename, strerror(errno));
        return -1;
    }
    
    now = time(NULL);
    
    fprintf(file, "# SimTemp CLI Configuration File\n");
    fprintf(file, "# Generated on %s", ctime(&now));
    fprintf(file, "# Edit this file to set default options\n\n");
    
    fprintf(file, "# Connection settings\n");
    fprintf(file, "connection_type = %s\n", 
            config->conn_type == CONNECTION_SSH ? "ssh" :
            config->conn_type == CONNECTION_TELNET ? "telnet" : "local");
    
    if (strlen(config->remote_host) > 0) {
        fprintf(file, "remote_host = %s\n", config->remote_host);
    }
    
    if (config->remote_port != 22) {
        fprintf(file, "remote_port = %d\n", config->remote_port);
    }
    
    if (strlen(config->username) > 0) {
        fprintf(file, "username = %s\n", config->username);
    }
    
    if (strlen(config->keyfile) > 0) {
        fprintf(file, "keyfile = %s\n", config->keyfile);
    }
    
    fprintf(file, "\n# Device paths\n");
    fprintf(file, "device_path = %s\n", config->device_path);
    fprintf(file, "sysfs_base = %s\n", config->sysfs_base);
    
    fprintf(file, "\n# Sensor configuration\n");
    if (config->sampling_ms > 0) {
        fprintf(file, "sampling_ms = %d\n", config->sampling_ms);
    }
    
    if (config->threshold_mc > -200000) {
        fprintf(file, "threshold_mc = %d\n", config->threshold_mc);
    }
    
    if (strlen(config->mode) > 0) {
        fprintf(file, "mode = %s\n", config->mode);
    }
    
    fprintf(file, "\n# Operation settings\n");
    fprintf(file, "poll_timeout_ms = %d\n", config->poll_timeout_ms);
    fprintf(file, "verbose = %s\n", config->verbose ? "true" : "false");
    fprintf(file, "json_output = %s\n", config->json_output ? "true" : "false");
    fprintf(file, "csv_output = %s\n", config->csv_output ? "true" : "false");
    
    fprintf(file, "\n# End of configuration\n");
    
    fclose(file);
    
    printf("Configuration saved to %s\n", filename);
    return 0;
}
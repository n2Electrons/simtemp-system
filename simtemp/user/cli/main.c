/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Main Implementation
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Command-line interface for NXP SimTemp temperature sensor driver.
 * Supports local and remote (SSH) communication for configuration,
 * monitoring, and real-time temperature display.
 */

#include "simtemp_cli.h"
#include <getopt.h>
#include <stdarg.h>

/* Global variables */
volatile bool g_running = true;
struct cli_stats g_stats;

/* Signal handler for graceful shutdown */
void signal_handler(int sig)
{
    printf("\nReceived signal %d, shutting down gracefully...\n", sig);
    g_running = false;
}

void setup_signal_handlers(void)
{
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
}

void print_usage(const char *program_name)
{
    printf("Usage: %s [OPTIONS] [COMMAND]\n\n", program_name);
    
    printf("SimTemp CLI - Temperature Sensor Control Interface v%s\n\n", CLI_VERSION);
    
    printf("CONNECTION OPTIONS:\n");
    printf("  -h, --host HOST         Remote host (enables SSH mode)\n");
    printf("  -p, --port PORT         SSH port (default: 22)\n");
    printf("  -u, --user USER         SSH username\n");
    printf("  -k, --keyfile FILE      SSH private key file\n");
    printf("  -t, --telnet            Use telnet instead of SSH\n\n");
    
    printf("DEVICE OPTIONS:\n");
    printf("  -d, --device PATH       Device path (default: %s)\n", DEFAULT_DEVICE_PATH);
    printf("  -s, --sysfs PATH        Sysfs base path (default: %s)\n", DEFAULT_SYSFS_BASE);
    printf("\n");
    
    printf("CONFIGURATION COMMANDS:\n");
    printf("  --config                Configure sensor parameters\n");
    printf("  --sampling MS           Set sampling period in milliseconds\n");
    printf("  --threshold TEMP        Set threshold in milli-degrees Celsius\n");
    printf("  --mode MODE             Set sensor mode (normal, noisy, ramp)\n");
    printf("  --status                Show current sensor status\n\n");
    
    printf("MONITORING COMMANDS:\n");
    printf("  --monitor               Monitor temperature in real-time\n");
    printf("  --duration SECONDS      Monitor for specified duration\n");
    printf("  --count SAMPLES         Read specified number of samples\n");
    printf("  --timeout MS            Poll timeout in milliseconds\n\n");
    
    printf("OUTPUT OPTIONS:\n");
    printf("  --json                  Output in JSON format\n");
    printf("  --csv                   Output in CSV format\n");
    printf("  --raw                   Output raw binary data\n");
    printf("  -v, --verbose           Enable verbose output\n\n");
    
    printf("OTHER OPTIONS:\n");
    printf("  --test                  Run test mode\n");
    printf("  --config-file FILE      Load configuration from file\n");
    printf("  --help                  Show this help message\n");
    printf("  --version               Show version information\n\n");
    
    printf("EXAMPLES:\n");
    printf("  # Local monitoring for 30 seconds\n");
    printf("  %s --monitor --duration 30\n\n", program_name);
    
    printf("  # Configure remote sensor via SSH\n");
    printf("  %s -h 192.168.1.100 -u root --config --sampling 500 --threshold 50000\n\n", program_name);
    
    printf("  # Monitor remote temperature with JSON output\n");
    printf("  %s -h 192.168.1.100 -u root --monitor --json --count 100\n\n", program_name);
    
    printf("  # Show status of local sensor\n");
    printf("  %s --status\n\n", program_name);
    
    printf("  # Run test mode on remote device\n");
    printf("  %s -h target.local -u admin --test\n\n", program_name);
}

void print_version(void)
{
    printf("%s version %s\n", CLI_NAME, CLI_VERSION);
    printf("Copyright (c) 2025 Jorge Rodriguez Moreno\n");
    printf("Licensed under GPL-2.0+\n");
}

void init_default_config(struct cli_config *config)
{
    memset(config, 0, sizeof(*config));
    
    config->conn_type = CONNECTION_LOCAL;
    config->remote_port = 22;
    
    strncpy(config->device_path, DEFAULT_DEVICE_PATH, sizeof(config->device_path) - 1);
    strncpy(config->sysfs_base, DEFAULT_SYSFS_BASE, sizeof(config->sysfs_base) - 1);
    
    config->poll_timeout_ms = DEFAULT_POLL_TIMEOUT;
    config->sampling_ms = -1;  /* Not set */
    config->threshold_mc = -1; /* Not set */
    
    strncpy(config->mode, "normal", sizeof(config->mode) - 1);
}

int parse_arguments(int argc, char *argv[], struct cli_config *config)
{
    static struct option long_options[] = {
        {"host",        required_argument, 0, 'h'},
        {"port",        required_argument, 0, 'p'},
        {"user",        required_argument, 0, 'u'},
        {"keyfile",     required_argument, 0, 'k'},
        {"telnet",      no_argument,       0, 't'},
        {"device",      required_argument, 0, 'd'},
        {"sysfs",       required_argument, 0, 's'},
        {"config",      no_argument,       0, 'C'},
        {"sampling",    required_argument, 0, 'S'},
        {"threshold",   required_argument, 0, 'T'},
        {"mode",        required_argument, 0, 'M'},
        {"status",      no_argument,       0, 'I'},
        {"monitor",     no_argument,       0, 'm'},
        {"duration",    required_argument, 0, 'D'},
        {"count",       required_argument, 0, 'N'},
        {"timeout",     required_argument, 0, 'O'},
        {"json",        no_argument,       0, 'j'},
        {"csv",         no_argument,       0, 'c'},
        {"raw",         no_argument,       0, 'r'},
        {"verbose",     no_argument,       0, 'v'},
        {"test",        no_argument,       0, 'e'},
        {"config-file", required_argument, 0, 'f'},
        {"help",        no_argument,       0, 'H'},
        {"version",     no_argument,       0, 'V'},
        {0, 0, 0, 0}
    };
    
    int c;
    int option_index = 0;
    
    while ((c = getopt_long(argc, argv, "h:p:u:k:td:s:CS:T:M:ImD:N:O:jcrvef:HV", 
                           long_options, &option_index)) != -1) {
        switch (c) {
        case 'h':
            strncpy(config->remote_host, optarg, sizeof(config->remote_host) - 1);
            config->conn_type = CONNECTION_SSH;
            break;
        case 'p':
            config->remote_port = atoi(optarg);
            break;
        case 'u':
            strncpy(config->username, optarg, sizeof(config->username) - 1);
            break;
        case 'k':
            strncpy(config->keyfile, optarg, sizeof(config->keyfile) - 1);
            break;
        case 't':
            config->conn_type = CONNECTION_TELNET;
            break;
        case 'd':
            strncpy(config->device_path, optarg, sizeof(config->device_path) - 1);
            break;
        case 's':
            strncpy(config->sysfs_base, optarg, sizeof(config->sysfs_base) - 1);
            break;
        case 'C':
            config->config_mode = true;
            break;
        case 'S':
            config->sampling_ms = atoi(optarg);
            break;
        case 'T':
            config->threshold_mc = atoi(optarg);
            break;
        case 'M':
            strncpy(config->mode, optarg, sizeof(config->mode) - 1);
            break;
        case 'I':
            config->status_mode = true;
            break;
        case 'm':
            config->monitor_mode = true;
            break;
        case 'D':
            config->duration_sec = atoi(optarg);
            break;
        case 'N':
            config->sample_count = atoi(optarg);
            break;
        case 'O':
            config->poll_timeout_ms = atoi(optarg);
            break;
        case 'j':
            config->json_output = true;
            break;
        case 'c':
            config->csv_output = true;
            break;
        case 'r':
            config->raw_output = true;
            break;
        case 'v':
            config->verbose = true;
            break;
        case 'e':
            config->test_mode = true;
            break;
        case 'f':
            return load_config_file(optarg, config);
        case 'H':
            print_usage(argv[0]);
            exit(0);
        case 'V':
            print_version();
            exit(0);
        case '?':
            return -1;
        default:
            return -1;
        }
    }
    
    return 0;
}

void print_error(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    fprintf(stderr, "ERROR: ");
    vfprintf(stderr, format, args);
    fprintf(stderr, "\n");
    va_end(args);
}

void print_verbose(const struct cli_config *config, const char *format, ...)
{
    if (!config->verbose) return;
    
    va_list args;
    va_start(args, format);
    printf("VERBOSE: ");
    vprintf(format, args);
    printf("\n");
    va_end(args);
}

double millicelsius_to_celsius(int32_t temp_mc)
{
    return (double)temp_mc / 1000.0;
}

int32_t celsius_to_millicelsius(double temp_c)
{
    return (int32_t)(temp_c * 1000.0);
}

void format_timestamp(uint64_t timestamp_ns, char *buffer, size_t buffer_size)
{
    time_t seconds = timestamp_ns / 1000000000ULL;
    uint32_t nanoseconds = timestamp_ns % 1000000000ULL;
    uint32_t milliseconds = nanoseconds / 1000000;
    
    struct tm *tm_info = gmtime(&seconds);
    
    snprintf(buffer, buffer_size, "%04d-%02d-%02dT%02d:%02d:%02d.%03uZ",
             tm_info->tm_year + 1900, tm_info->tm_mon + 1, tm_info->tm_mday,
             tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec, milliseconds);
}

void print_temperature_sample(const struct simtemp_record *record, const struct cli_config *config)
{
    if (config->json_output) {
        print_json_sample(record);
    } else if (config->csv_output) {
        print_csv_sample(record);
    } else {
        /* Standard format: 2025-09-22T20:15:04.123Z temp=44.1C alert=0 */
        char timestamp_str[64];
        format_timestamp(record->timestamp_ns, timestamp_str, sizeof(timestamp_str));
        
        double temp_c = millicelsius_to_celsius(record->temp_mC);
        int alert = (record->flags & SIMTEMP_FLAG_THRESHOLD_CROSSED) ? 1 : 0;
        
        printf("%s temp=%.1fC alert=%d\n", timestamp_str, temp_c, alert);
    }
}

void print_json_sample(const struct simtemp_record *record)
{
    char timestamp_str[64];
    format_timestamp(record->timestamp_ns, timestamp_str, sizeof(timestamp_str));
    
    double temp_c = millicelsius_to_celsius(record->temp_mC);
    bool new_sample = record->flags & SIMTEMP_FLAG_NEW_SAMPLE;
    bool threshold_crossed = record->flags & SIMTEMP_FLAG_THRESHOLD_CROSSED;
    
    printf("{\n");
    printf("  \"timestamp\": \"%s\",\n", timestamp_str);
    printf("  \"timestamp_ns\": %lu,\n", record->timestamp_ns);
    printf("  \"temperature_celsius\": %.3f,\n", temp_c);
    printf("  \"temperature_millicelsius\": %d,\n", record->temp_mC);
    printf("  \"flags\": %u,\n", record->flags);
    printf("  \"new_sample\": %s,\n", new_sample ? "true" : "false");
    printf("  \"threshold_crossed\": %s\n", threshold_crossed ? "true" : "false");
    printf("}\n");
}

void print_csv_sample(const struct simtemp_record *record)
{
    static bool header_printed = false;
    
    if (!header_printed) {
        printf("timestamp_ns,temperature_celsius,temperature_millicelsius,flags,new_sample,threshold_crossed\n");
        header_printed = true;
    }
    
    double temp_c = millicelsius_to_celsius(record->temp_mC);
    bool new_sample = record->flags & SIMTEMP_FLAG_NEW_SAMPLE;
    bool threshold_crossed = record->flags & SIMTEMP_FLAG_THRESHOLD_CROSSED;
    
    printf("%lu,%.3f,%d,%u,%s,%s\n",
           record->timestamp_ns, temp_c, record->temp_mC, record->flags,
           new_sample ? "true" : "false",
           threshold_crossed ? "true" : "false");
}

void init_stats(struct cli_stats *stats)
{
    memset(stats, 0, sizeof(*stats));
    stats->start_time = time(NULL);
    stats->min_temp = 1000.0;  /* Initialize to high value */
    stats->max_temp = -1000.0; /* Initialize to low value */
}

void update_stats(struct cli_stats *stats, const struct simtemp_record *record)
{
    double temp_c = millicelsius_to_celsius(record->temp_mC);
    
    stats->samples_read++;
    stats->last_sample_time = time(NULL);
    
    if (record->flags & SIMTEMP_FLAG_THRESHOLD_CROSSED) {
        stats->alerts_detected++;
    }
    
    if (temp_c < stats->min_temp) {
        stats->min_temp = temp_c;
    }
    if (temp_c > stats->max_temp) {
        stats->max_temp = temp_c;
    }
    
    /* Update running average */
    stats->avg_temp = ((stats->avg_temp * (stats->samples_read - 1)) + temp_c) / stats->samples_read;
}

void print_stats(const struct cli_stats *stats)
{
    time_t duration = stats->last_sample_time - stats->start_time;
    if (duration == 0) duration = 1;
    
    printf("\n=== Statistics ===\n");
    printf("Samples read: %lu\n", stats->samples_read);
    printf("Alerts detected: %lu\n", stats->alerts_detected);
    printf("Errors: %lu\n", stats->errors_count);
    printf("Duration: %ld seconds\n", duration);
    printf("Sample rate: %.2f samples/sec\n", (double)stats->samples_read / duration);
    
    if (stats->samples_read > 0) {
        printf("Temperature range: %.1f°C to %.1f°C\n", stats->min_temp, stats->max_temp);
        printf("Average temperature: %.1f°C\n", stats->avg_temp);
    }
    
    printf("\n");
}

bool validate_sampling_period(int period_ms)
{
    return (period_ms >= 1 && period_ms <= 60000);
}

bool validate_threshold(int threshold_mc)
{
    return (threshold_mc >= -50000 && threshold_mc <= 150000);
}

bool validate_mode(const char *mode)
{
    const char *valid_modes[] = {"normal", "noisy", "ramp", "static", "linear", NULL};
    
    for (int i = 0; valid_modes[i]; i++) {
        if (strcmp(mode, valid_modes[i]) == 0) {
            return true;
        }
    }
    return false;
}

const char *get_connection_type_string(connection_type_t type)
{
    switch (type) {
    case CONNECTION_LOCAL:
        return "Local";
    case CONNECTION_SSH:
        return "SSH";
    case CONNECTION_TELNET:
        return "Telnet";
    default:
        return "Unknown";
    }
}

int main(int argc, char *argv[])
{
    struct cli_config config;
    struct remote_context remote_ctx = {0};
    int result = 0;
    
    /* Initialize configuration with defaults */
    init_default_config(&config);
    
    /* Parse command line arguments */
    if (parse_arguments(argc, argv, &config) < 0) {
        print_error("Failed to parse command line arguments");
        return 1;
    }
    
    /* Setup signal handlers for graceful shutdown */
    setup_signal_handlers();
    
    /* Initialize statistics */
    init_stats(&g_stats);
    
    print_verbose(&config, "Starting %s v%s", CLI_NAME, CLI_VERSION);
    print_verbose(&config, "Connection type: %s", get_connection_type_string(config.conn_type));
    
    /* Connect to remote host if needed */
    if (is_remote_connection(&config)) {
        print_verbose(&config, "Connecting to remote host: %s:%d", 
                     config.remote_host, config.remote_port);
        
        if (connect_remote(&remote_ctx, &config) < 0) {
            print_error("Failed to connect to remote host");
            return 1;
        }
        
        print_verbose(&config, "Successfully connected to remote host");
    }
    
    /* Execute requested operations */
    if (config.test_mode) {
        print_verbose(&config, "Running test mode");
        result = run_test_mode(&config, &remote_ctx);
    } else if (config.config_mode) {
        print_verbose(&config, "Configuring sensor");
        result = configure_sensor(&config, &remote_ctx);
    } else if (config.monitor_mode) {
        print_verbose(&config, "Starting temperature monitoring");
        result = monitor_temperature(&config, &remote_ctx);
    } else if (config.status_mode) {
        print_verbose(&config, "Showing sensor status");
        result = show_sensor_status(&config, &remote_ctx);
    } else {
        /* Default action: show status */
        result = show_sensor_status(&config, &remote_ctx);
    }
    
    /* Cleanup */
    if (is_remote_connection(&config)) {
        disconnect_remote(&remote_ctx);
        print_verbose(&config, "Disconnected from remote host");
    }
    
    /* Print final statistics if monitoring was performed */
    if (config.monitor_mode && g_stats.samples_read > 0) {
        print_stats(&g_stats);
    }
    
    print_verbose(&config, "Program completed with exit code: %d", result);
    
    return result;
}
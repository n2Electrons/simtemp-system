/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * SimTemp CLI - Header File
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * Command-line interface for NXP SimTemp temperature sensor driver.
 * Supports local and remote (SSH) communication for configuration,
 * monitoring, and real-time temperature display.
 */

#ifndef _SIMTEMP_CLI_H_
#define _SIMTEMP_CLI_H_

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <poll.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <signal.h>

/* Version information */
#define CLI_VERSION "1.0.0"
#define CLI_NAME "simtemp-cli"

/* Default paths and settings */
#define DEFAULT_DEVICE_PATH "/dev/simtemp"
#define DEFAULT_SYSFS_BASE "/sys/class/misc/simtemp"
#define DEFAULT_SAMPLING_MS 1000
#define DEFAULT_THRESHOLD_MC 45000
#define DEFAULT_POLL_TIMEOUT 5000

/* Temperature record structure (must match kernel driver) */
struct simtemp_record {
    uint64_t timestamp_ns;   /* monotonic timestamp */
    int32_t temp_mC;        /* milli-degree Celsius */
    uint32_t flags;         /* bit0=NEW_SAMPLE, bit1=THRESHOLD_CROSSED */
    uint32_t reserved;      /* reserved for future use */
} __attribute__((packed));

/* Status flags */
#define SIMTEMP_FLAG_NEW_SAMPLE     0x01
#define SIMTEMP_FLAG_THRESHOLD_CROSSED 0x02

/* Connection types */
typedef enum {
    CONNECTION_LOCAL,
    CONNECTION_SSH,
    CONNECTION_TELNET
} connection_type_t;

/* CLI configuration */
struct cli_config {
    /* Connection settings */
    connection_type_t conn_type;
    char remote_host[256];
    int remote_port;
    char username[64];
    char password[64];  /* Not recommended, use key-based auth */
    char keyfile[512];
    
    /* Device paths */
    char device_path[512];
    char sysfs_base[512];
    
    /* Operation modes */
    bool monitor_mode;
    bool config_mode;
    bool status_mode;
    bool test_mode;
    bool verbose;
    
    /* Monitoring settings */
    int duration_sec;
    int sample_count;
    int poll_timeout_ms;
    
    /* Configuration values */
    int sampling_ms;
    int threshold_mc;
    char mode[32];
    
    /* Output formatting */
    bool json_output;
    bool csv_output;
    bool raw_output;
};

/* Remote command execution context */
struct remote_context {
    connection_type_t type;
    FILE *cmd_pipe;
    char host[256];
    int port;
    char user[64];
    bool connected;
};

/* Statistics tracking */
struct cli_stats {
    uint64_t samples_read;
    uint64_t alerts_detected;
    uint64_t errors_count;
    time_t start_time;
    time_t last_sample_time;
    double min_temp;
    double max_temp;
    double avg_temp;
};

/* Function prototypes */

/* Main CLI functions */
int parse_arguments(int argc, char *argv[], struct cli_config *config);
void print_usage(const char *program_name);
void print_version(void);

/* Configuration management */
int load_config_file(const char *filename, struct cli_config *config);
int save_config_file(const char *filename, const struct cli_config *config);
void init_default_config(struct cli_config *config);

/* Remote connection management */
int connect_remote(struct remote_context *ctx, const struct cli_config *config);
void disconnect_remote(struct remote_context *ctx);
int execute_remote_command(struct remote_context *ctx, const char *command, 
                          char *output, size_t output_size);
bool is_remote_connection(const struct cli_config *config);

/* Device operations */
int open_device(const char *device_path);
void close_device(int fd);
int read_temperature_sample(int fd, struct simtemp_record *record);
int wait_for_sample(int fd, int timeout_ms);

/* Sysfs configuration */
int read_sysfs_attribute(const char *base_path, const char *attr_name, 
                        char *value, size_t value_size);
int write_sysfs_attribute(const char *base_path, const char *attr_name, 
                         const char *value);
int get_sampling_period(const char *sysfs_base);
int set_sampling_period(const char *sysfs_base, int period_ms);
int get_threshold(const char *sysfs_base);
int set_threshold(const char *sysfs_base, int threshold_mc);
int get_mode(const char *sysfs_base, char *mode, size_t mode_size);
int set_mode(const char *sysfs_base, const char *mode);

/* Remote sysfs operations */
int remote_read_sysfs_attribute(struct remote_context *ctx, const char *base_path,
                               const char *attr_name, char *value, size_t value_size);
int remote_write_sysfs_attribute(struct remote_context *ctx, const char *base_path,
                                const char *attr_name, const char *value);
int remote_get_sampling_period(struct remote_context *ctx, const char *sysfs_base);
int remote_set_sampling_period(struct remote_context *ctx, const char *sysfs_base, int period_ms);
int remote_get_threshold(struct remote_context *ctx, const char *sysfs_base);
int remote_set_threshold(struct remote_context *ctx, const char *sysfs_base, int threshold_mc);

/* Monitoring functions */
int monitor_temperature(const struct cli_config *config, struct remote_context *ctx);
int monitor_local_temperature(const struct cli_config *config);
int monitor_remote_temperature(const struct cli_config *config, struct remote_context *ctx);

/* Configuration functions */
int configure_sensor(const struct cli_config *config, struct remote_context *ctx);
int show_sensor_status(const struct cli_config *config, struct remote_context *ctx);

/* Test mode */
int run_test_mode(const struct cli_config *config, struct remote_context *ctx);

/* Output formatting */
void format_timestamp(uint64_t timestamp_ns, char *buffer, size_t buffer_size);
void print_temperature_sample(const struct simtemp_record *record, const struct cli_config *config);
void print_json_sample(const struct simtemp_record *record);
void print_csv_sample(const struct simtemp_record *record);
void print_status_info(const struct cli_config *config, struct remote_context *ctx);

/* Utility functions */
double millicelsius_to_celsius(int32_t temp_mc);
int32_t celsius_to_millicelsius(double temp_c);
const char *get_connection_type_string(connection_type_t type);
void signal_handler(int sig);
void setup_signal_handlers(void);

/* Statistics functions */
void init_stats(struct cli_stats *stats);
void update_stats(struct cli_stats *stats, const struct simtemp_record *record);
void print_stats(const struct cli_stats *stats);

/* Error handling */
void print_error(const char *format, ...);
void print_verbose(const struct cli_config *config, const char *format, ...);
void print_debug(const struct cli_config *config, const char *format, ...);

/* SSH command builders */
int build_ssh_command(const struct cli_config *config, const char *remote_cmd, 
                     char *full_cmd, size_t cmd_size);
int build_scp_command(const struct cli_config *config, const char *local_file,
                     const char *remote_file, char *full_cmd, size_t cmd_size);

/* Configuration validation */
bool validate_sampling_period(int period_ms);
bool validate_threshold(int threshold_mc);
bool validate_mode(const char *mode);
bool validate_connection_config(const struct cli_config *config);

/* Global variables */
extern volatile bool g_running;
extern struct cli_stats g_stats;

#endif /* _SIMTEMP_CLI_H_ */
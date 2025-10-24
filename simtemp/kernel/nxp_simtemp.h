/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * NXP SimTemp Temperature Simulator Driver Header
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 *
 * This header defines the interface and data structures for the NXP SimTemp
 * temperature simulator character driver. It provides temperature simulation
 * capabilities for embedded systems development and testing.
 */

#ifndef _NXP_SIMTEMP_H_
#define _NXP_SIMTEMP_H_

#include <linux/types.h>
#include <linux/device.h>
#include <linux/cdev.h>
#include <linux/mutex.h>
#include <linux/ioctl.h>

/* Driver identification */
#define DRIVER_NAME		"nxp-simtemp"
#define DRIVER_VERSION		"1.0.0"
#define DEVICE_NAME		"simtemp"
#define CLASS_NAME		"simtemp_class"

/* Default values */
#define DEFAULT_TEMPERATURE	25000	/* 25°C in milliCelsius */
#define DEFAULT_SAMPLING_MS	1000	/* 1 second */
#define DEFAULT_THRESHOLD_MC	50000	/* 50°C in milliCelsius */
#define DEFAULT_MODE		"simulation"

/* Temperature limits */
#define MIN_TEMPERATURE		-40000	/* -40°C in milliCelsius */
#define MAX_TEMPERATURE		125000	/* 125°C in milliCelsius */

/* Character device limits */
#define MAX_DEVICES		4
#define BUFFER_SIZE		256

/* IOCTL magic number and commands */
#define SIMTEMP_IOC_MAGIC	'T'
#define SIMTEMP_IOC_MAXNR	10

/* IOCTL command definitions */
#define SIMTEMP_IOC_GET_TEMP		_IOR(SIMTEMP_IOC_MAGIC, 1, int)
#define SIMTEMP_IOC_SET_TEMP		_IOW(SIMTEMP_IOC_MAGIC, 2, int)
#define SIMTEMP_IOC_GET_SAMPLING	_IOR(SIMTEMP_IOC_MAGIC, 3, u32)
#define SIMTEMP_IOC_SET_SAMPLING	_IOW(SIMTEMP_IOC_MAGIC, 4, u32)
#define SIMTEMP_IOC_GET_THRESHOLD	_IOR(SIMTEMP_IOC_MAGIC, 5, u32)
#define SIMTEMP_IOC_SET_THRESHOLD	_IOW(SIMTEMP_IOC_MAGIC, 6, u32)
#define SIMTEMP_IOC_GET_MODE		_IOR(SIMTEMP_IOC_MAGIC, 7, char[32])
#define SIMTEMP_IOC_SET_MODE		_IOW(SIMTEMP_IOC_MAGIC, 8, char[32])
#define SIMTEMP_IOC_RESET		_IO(SIMTEMP_IOC_MAGIC, 9)
#define SIMTEMP_IOC_GET_STATUS		_IOR(SIMTEMP_IOC_MAGIC, 10, struct simtemp_status)

/**
 * enum simtemp_mode - Operating modes for the temperature simulator
 * @SIMTEMP_MODE_STATIC: Static temperature, no changes
 * @SIMTEMP_MODE_LINEAR: Linear temperature changes
 * @SIMTEMP_MODE_RANDOM: Random temperature variations
 * @SIMTEMP_MODE_SINE: Sinusoidal temperature pattern
 */
enum simtemp_mode {
	SIMTEMP_MODE_STATIC = 0,
	SIMTEMP_MODE_LINEAR,
	SIMTEMP_MODE_RANDOM,
	SIMTEMP_MODE_SINE,
	SIMTEMP_MODE_MAX
};

/**
 * struct simtemp_status - Status information structure
 * @temperature: Current temperature in milliCelsius
 * @sampling_ms: Sampling interval in milliseconds
 * @threshold_mC: Temperature threshold in milliCelsius
 * @mode: Current operating mode
 * @is_active: Device active status
 * @error_count: Number of errors encountered
 * @read_count: Number of read operations
 * @write_count: Number of write operations
 */
struct simtemp_status {
	int temperature;
	u32 sampling_ms;
	u32 threshold_mC;
	enum simtemp_mode mode;
	bool is_active;
	u32 error_count;
	u32 read_count;
	u32 write_count;
};

/**
 * struct nxp_simtemp_data - Private data structure for the driver
 * @dev: Device pointer
 * @pdev: Platform device pointer
 * @cdev: Character device structure
 * @device: Device class device
 * @class: Device class
 * @devt: Device number
 * @mutex: Mutex for thread-safe operations
 * @temperature: Current simulated temperature in milliCelsius
 * @sampling_ms: Sampling interval in milliseconds
 * @threshold_mC: Temperature threshold in milliCelsius
 * @mode: Operating mode string
 * @mode_enum: Operating mode enumeration
 * @is_open: Device open status
 * @open_count: Number of times device has been opened
 * @status: Device status structure
 * @buffer: Internal buffer for read/write operations
 * @buffer_size: Current buffer size
 */
struct nxp_simtemp_data {
	struct device *dev;
	struct platform_device *pdev;
	struct cdev cdev;
	struct device *device;
	struct class *class;
	dev_t devt;
	struct mutex mutex;
	
	/* Temperature simulation data */
	int temperature;
	u32 sampling_ms;
	u32 threshold_mC;
	const char *mode;
	enum simtemp_mode mode_enum;
	
	/* Character device state */
	bool is_open;
	u32 open_count;
	struct simtemp_status status;
	
	/* Buffer management */
	char buffer[BUFFER_SIZE];
	size_t buffer_size;
};

/* Function prototypes for character device operations */
int nxp_simtemp_open(struct inode *inode, struct file *filp);
int nxp_simtemp_release(struct inode *inode, struct file *filp);
ssize_t nxp_simtemp_read(struct file *filp, char __user *buf, 
			 size_t count, loff_t *f_pos);
ssize_t nxp_simtemp_write(struct file *filp, const char __user *buf, 
			  size_t count, loff_t *f_pos);
long nxp_simtemp_ioctl(struct file *filp, unsigned int cmd, 
		       unsigned long arg);

/* Utility function prototypes */
int nxp_simtemp_validate_temperature(int temp);
int nxp_simtemp_validate_sampling(u32 sampling_ms);
int nxp_simtemp_validate_threshold(u32 threshold_mC);
const char *nxp_simtemp_mode_to_string(enum simtemp_mode mode);
enum simtemp_mode nxp_simtemp_string_to_mode(const char *mode_str);

/* Platform driver function prototypes */
int nxp_simtemp_probe(struct platform_device *pdev);
#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 11, 0)
void nxp_simtemp_remove(struct platform_device *pdev);
#else
int nxp_simtemp_remove(struct platform_device *pdev);
#endif

/* Module initialization/cleanup */
int __init nxp_simtemp_init(void);
void __exit nxp_simtemp_exit(void);

/* Sysfs attribute function prototypes */
ssize_t sampling_ms_show(struct device *dev, struct device_attribute *attr, 
			 char *buf);
ssize_t sampling_ms_store(struct device *dev, struct device_attribute *attr,
			  const char *buf, size_t count);
ssize_t threshold_mC_show(struct device *dev, struct device_attribute *attr, 
			  char *buf);
ssize_t threshold_mC_store(struct device *dev, struct device_attribute *attr,
			   const char *buf, size_t count);
ssize_t mode_show(struct device *dev, struct device_attribute *attr, 
		  char *buf);
ssize_t mode_store(struct device *dev, struct device_attribute *attr,
		   const char *buf, size_t count);
ssize_t temperature_show(struct device *dev, struct device_attribute *attr,
			 char *buf);
ssize_t temperature_store(struct device *dev, struct device_attribute *attr,
			  const char *buf, size_t count);
ssize_t status_show(struct device *dev, struct device_attribute *attr,
		    char *buf);

/* Inline helper functions */

/**
 * nxp_simtemp_celsius_to_millicelsius() - Convert Celsius to milliCelsius
 * @celsius: Temperature in Celsius
 *
 * Return: Temperature in milliCelsius
 */
static inline int nxp_simtemp_celsius_to_millicelsius(int celsius)
{
	return celsius * 1000;
}

/**
 * nxp_simtemp_millicelsius_to_celsius() - Convert milliCelsius to Celsius
 * @millicelsius: Temperature in milliCelsius
 *
 * Return: Temperature in Celsius
 */
static inline int nxp_simtemp_millicelsius_to_celsius(int millicelsius)
{
	return millicelsius / 1000;
}

/**
 * nxp_simtemp_is_valid_device() - Check if device data is valid
 * @data: Device data structure
 *
 * Return: true if valid, false otherwise
 */
static inline bool nxp_simtemp_is_valid_device(struct nxp_simtemp_data *data)
{
	return data && data->dev;
}

#endif /* _NXP_SIMTEMP_H_ */
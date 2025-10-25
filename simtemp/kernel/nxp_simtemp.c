// SPDX-License-Identifier: GPL-2.0+
/*
 *  Temperature Simulator Driver
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 */

#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/of_device.h>
#include <linux/slab.h>
#include <linux/err.h>
#include <linux/version.h>
#include <linux/sysfs.h>
#include <linux/device.h>
#include <linux/types.h>
#include <linux/kernel.h>
#include <linux/delay.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/mutex.h>
#include <linux/wait.h>
#include <linux/poll.h>
#include <linux/timer.h>
#include <linux/jiffies.h>

#include "nxp_simtemp.h"

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Jorge Rodriguez Moreno");
MODULE_DESCRIPTION("Temperature Simulator Driver with Clean Load/Unload Support");
MODULE_VERSION("1.0.0");

/* For x86 systems without Device Tree, request the stub module */
#ifdef CONFIG_X86
MODULE_SOFTDEP("pre: nxp_simtemp_stub");
#endif

#define DRIVER_NAME "nxp-simtemp"
#define DEVICE_NAME "simtemp"
#define CLASS_NAME "simtemp_class"

/**
 * Sysfs show functions with safety checks
 */
static ssize_t sampling_ms_show(struct device *dev,
				struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	return sprintf(buf, "%u\n", data->sampling_ms);
}

/* Forward declarations */
static void simtemp_update_record(struct nxp_simtemp_data *data);
static int simtemp_generate_temperature(struct nxp_simtemp_data *data);

/**
 * F-K2: Timer callback for periodic sampling
 */
static void simtemp_timer_callback(struct timer_list *t)
{
	struct nxp_simtemp_data *data = from_timer(data, t, sample_timer);
	
	mutex_lock(&data->mutex);
	
	/* Generate new temperature value based on current mode */
	simtemp_generate_temperature(data);
	
	/* Update record with new temperature */
	simtemp_update_record(data);
	
	/* Reschedule if timer is active */
	if (data->timer_active) {
		mod_timer(&data->sample_timer, 
			  jiffies + msecs_to_jiffies(data->sampling_ms));
	}
	mutex_unlock(&data->mutex);
}

/**
 * F-K2: Start periodic sampling timer
 */
static void simtemp_start_sampling(struct nxp_simtemp_data *data)
{
	if (!data->timer_active) {
		data->timer_active = true;
		mod_timer(&data->sample_timer,
			  jiffies + msecs_to_jiffies(data->sampling_ms));
		dev_info(data->dev, "Started periodic sampling every %u ms\n", 
			 data->sampling_ms);
	}
}

/**
 * F-K2: Stop periodic sampling timer
 */
static void simtemp_stop_sampling(struct nxp_simtemp_data *data)
{
	if (data->timer_active) {
		data->timer_active = false;
		del_timer_sync(&data->sample_timer);
		dev_info(data->dev, "Stopped periodic sampling\n");
	}
}

/**
 * F-K2: Make sampling_ms writable for runtime adjustment
 */
static ssize_t sampling_ms_store(struct device *dev,
				 struct device_attribute *attr,
				 const char *buf, size_t count)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	u32 new_sampling_ms;
	int ret;
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	ret = kstrtou32(buf, 10, &new_sampling_ms);
	if (ret)
		return ret;
	
	/* Validate range: 100ms to 10s */
	if (new_sampling_ms < 100 || new_sampling_ms > 10000) {
		dev_warn(dev, "Invalid sampling_ms %u (valid: 100-10000)\n", 
			 new_sampling_ms);
		return -EINVAL;
	}
	
	mutex_lock(&data->mutex);
	data->sampling_ms = new_sampling_ms;
	
	/* Restart timer with new interval if active */
	if (data->timer_active) {
		del_timer_sync(&data->sample_timer);
		mod_timer(&data->sample_timer,
			  jiffies + msecs_to_jiffies(data->sampling_ms));
		dev_info(data->dev, "Updated sampling interval to %u ms\n", 
			 data->sampling_ms);
	}
	mutex_unlock(&data->mutex);
	
	return count;
}

static ssize_t threshold_mC_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	return sprintf(buf, "%u\n", data->threshold_mC);
}

static ssize_t threshold_mC_store(struct device *dev,
				  struct device_attribute *attr,
				  const char *buf, size_t count)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	u32 new_threshold_mC;
	int ret;
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	ret = kstrtou32(buf, 10, &new_threshold_mC);
	if (ret)
		return ret;
	
	/* Validate range: -40°C to 125°C in mC */
	if (new_threshold_mC > 125000) {
		dev_warn(dev, "Invalid threshold_mC %u (valid: 0-125000)\n", 
			 new_threshold_mC);
		return -EINVAL;
	}
	
	mutex_lock(&data->mutex);
	data->threshold_mC = new_threshold_mC;
	mutex_unlock(&data->mutex);
	
	dev_info(dev, "Updated threshold to %u mC (%u.%03u°C)\n", 
		 new_threshold_mC, new_threshold_mC / 1000, 
		 new_threshold_mC % 1000);
	
	return count;
}

static ssize_t mode_show(struct device *dev,
			 struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	return sprintf(buf, "%s\n", data->mode);
}

static ssize_t stats_show(struct device *dev,
			  struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	return sprintf(buf, "alerts: %u\ntemperature: %d\nsampling_ms: %u\nthreshold_mC: %u\n",
		       data->alert_count, data->temperature * 1000, 
		       data->sampling_ms, data->threshold_mC);
}

static ssize_t temp_pattern_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	const char *pattern_names[] = {
		"static", "linear", "exponential", "sinusoidal", 
		"step", "noisy", "realistic"
	};
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	if (data->temp_generator.pattern_type >= SIMTEMP_MODE_MAX) {
		return sprintf(buf, "unknown\n");
	}
	
	return sprintf(buf, "%s\n", pattern_names[data->temp_generator.pattern_type]);
}

static ssize_t temp_pattern_store(struct device *dev,
				  struct device_attribute *attr,
				  const char *buf, size_t count)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	char pattern_name[32];
	enum simtemp_mode new_pattern = SIMTEMP_MODE_STATIC;
	
	if (!data) {
		dev_warn(dev, "Device data not available\n");
		return -ENODEV;
	}
	
	if (sscanf(buf, "%31s", pattern_name) != 1) {
		dev_err(dev, "Invalid pattern name\n");
		return -EINVAL;
	}
	
	/* Parse pattern name */
	if (strcmp(pattern_name, "static") == 0) {
		new_pattern = SIMTEMP_MODE_STATIC;
	} else if (strcmp(pattern_name, "linear") == 0) {
		new_pattern = SIMTEMP_MODE_LINEAR;
	} else if (strcmp(pattern_name, "exponential") == 0) {
		new_pattern = SIMTEMP_MODE_EXPONENTIAL;
	} else if (strcmp(pattern_name, "sinusoidal") == 0) {
		new_pattern = SIMTEMP_MODE_SINUSOIDAL;
	} else if (strcmp(pattern_name, "step") == 0) {
		new_pattern = SIMTEMP_MODE_STEP;
	} else if (strcmp(pattern_name, "noisy") == 0) {
		new_pattern = SIMTEMP_MODE_NOISY;
	} else if (strcmp(pattern_name, "realistic") == 0) {
		new_pattern = SIMTEMP_MODE_REALISTIC;
	} else {
		dev_err(dev, "Unknown pattern: %s\n", pattern_name);
		dev_info(dev, "Valid patterns: static, linear, exponential, sinusoidal, step, noisy, realistic\n");
		return -EINVAL;
	}
	
	mutex_lock(&data->mutex);
	data->temp_generator.pattern_type = new_pattern;
	data->temp_generator.sample_count = 0;  /* Reset pattern */
	mutex_unlock(&data->mutex);
	
	dev_info(dev, "Temperature pattern changed to: %s\n", pattern_name);
	return count;
}

/* Define device attributes */
static DEVICE_ATTR(sampling_ms, 0644, sampling_ms_show, sampling_ms_store);
static DEVICE_ATTR(threshold_mC, 0644, threshold_mC_show, threshold_mC_store);
static DEVICE_ATTR_RO(mode);
static DEVICE_ATTR_RO(stats);
static DEVICE_ATTR(temp_pattern, 0644, temp_pattern_show, temp_pattern_store);

/* Attribute group */
static struct attribute *nxp_simtemp_attrs[] = {
	&dev_attr_sampling_ms.attr,
	&dev_attr_threshold_mC.attr,
	&dev_attr_mode.attr,
	&dev_attr_stats.attr,
	&dev_attr_temp_pattern.attr,
	NULL,
};

static const struct attribute_group nxp_simtemp_group = {
	.attrs = nxp_simtemp_attrs,
};

static const struct attribute_group *nxp_simtemp_groups[] = {
	&nxp_simtemp_group,
	NULL
};

/* Global variables for character device */
static dev_t simtemp_devt;
static struct class *simtemp_class;
static int device_count = 0;

/**
 * simtemp_generate_temperature - Generate dynamic temperature based on mode
 * @data: Device data structure
 *
 * This function implements various temperature generation patterns:
 * - STATIC: No change
 * - LINEAR: Linear ramp from min to max temperature
 * - EXPONENTIAL: Exponential heating curve
 * - SINUSOIDAL: Sinusoidal temperature variation
 * - STEP: Step changes between temperature levels
 * - NOISY: Linear ramp with Gaussian noise
 * - REALISTIC: Complex environmental simulation
 */
static int simtemp_generate_temperature(struct nxp_simtemp_data *data)
{
	u32 elapsed_ms;
	int new_temp = data->temperature;
	int temp_range, progress_percent;
	u64 current_time_ns = ktime_get_ns();
	
	if (!data->temp_generator.enabled) {
		return data->temperature;
	}
	
	/* Calculate elapsed time since pattern start */
	elapsed_ms = data->temp_generator.sample_count * data->sampling_ms;
	data->temp_generator.sample_count++;
	
	/* Generate temperature based on pattern type */
	switch (data->temp_generator.pattern_type) {
	case SIMTEMP_MODE_STATIC:
		/* No change - keep current temperature */
		break;
		
	case SIMTEMP_MODE_LINEAR:
		/* Linear ramp: T = T_min + (T_max - T_min) * (t / period) */
		if (data->temp_generator.period_ms > 0) {
			progress_percent = (elapsed_ms % data->temp_generator.period_ms) * 100 / 
					   data->temp_generator.period_ms;
			temp_range = data->temp_generator.max_temp - data->temp_generator.min_temp;
			new_temp = data->temp_generator.min_temp + (temp_range * progress_percent / 100);
		}
		break;
		
	case SIMTEMP_MODE_EXPONENTIAL:
		/* Exponential heating: T = T_min + (T_max - T_min) * (1 - exp(-t/tau)) */
		if (data->temp_generator.period_ms > 0) {
			/* Use period_ms as time constant (tau) in milliseconds */
			int tau_ms = data->temp_generator.period_ms / 3; /* tau = period/3 for 95% completion */
			int exp_factor = 1000 - (1000 * elapsed_ms / (elapsed_ms + tau_ms)); /* Approximation */
			temp_range = data->temp_generator.max_temp - data->temp_generator.min_temp;
			new_temp = data->temp_generator.min_temp + (temp_range * (1000 - exp_factor) / 1000);
		}
		break;
		
	case SIMTEMP_MODE_SINUSOIDAL:
		/* Sinusoidal: T = T_base + amplitude * sin(2*pi*t/period) */
		if (data->temp_generator.period_ms > 0) {
			/* Simple sine approximation using lookup table approach */
			int phase = (elapsed_ms % data->temp_generator.period_ms) * 360 / data->temp_generator.period_ms;
			int sine_approx = 0;
			
			/* Simple sine approximation (good enough for kernel space) */
			if (phase < 90) {
				sine_approx = phase * 1000 / 90;  /* 0 to 1000 (0 to 1.0) */
			} else if (phase < 180) {
				sine_approx = (180 - phase) * 1000 / 90;  /* 1000 to 0 */
			} else if (phase < 270) {
				sine_approx = -(phase - 180) * 1000 / 90;  /* 0 to -1000 */
			} else {
				sine_approx = -(360 - phase) * 1000 / 90;  /* -1000 to 0 */
			}
			
			new_temp = data->temp_generator.base_temperature + 
				   (data->temp_generator.amplitude * sine_approx / 1000);
		}
		break;
		
	case SIMTEMP_MODE_STEP:
		/* Step pattern: Change temperature every period/4 */
		if (data->temp_generator.period_ms > 0) {
			int step_duration = data->temp_generator.period_ms / 4;
			int step_index = (elapsed_ms / step_duration) % 4;
			int step_temps[] = {
				data->temp_generator.min_temp,
				data->temp_generator.base_temperature,
				data->temp_generator.max_temp,
				data->temp_generator.base_temperature
			};
			new_temp = step_temps[step_index];
		}
		break;
		
	case SIMTEMP_MODE_NOISY:
		/* Linear ramp with noise */
		/* First calculate linear ramp */
		if (data->temp_generator.period_ms > 0) {
			progress_percent = (elapsed_ms % data->temp_generator.period_ms) * 100 / 
					   data->temp_generator.period_ms;
			temp_range = data->temp_generator.max_temp - data->temp_generator.min_temp;
			new_temp = data->temp_generator.min_temp + (temp_range * progress_percent / 100);
		}
		/* Add simple noise (using current time as pseudo-random source) */
		{
			u32 noise_seed = (u32)(current_time_ns & 0xFFFFFFFF);
			int noise = ((int)(noise_seed % 2000) - 1000) * data->temp_generator.noise_level / 1000;
			new_temp += noise;
		}
		break;
		
	case SIMTEMP_MODE_REALISTIC:
		/* Complex environmental simulation */
		/* Base exponential heating with multiple frequency components */
		if (data->temp_generator.period_ms > 0) {
			/* Variable declarations at beginning of block */
			int tau_ms = data->temp_generator.period_ms / 2;
			int exp_factor = 1000 - (1000 * elapsed_ms / (elapsed_ms + tau_ms));
			int hvac_phase = (elapsed_ms % (data->temp_generator.period_ms * 2)) * 360 / 
					 (data->temp_generator.period_ms * 2);
			int hvac_effect = data->temp_generator.amplitude * hvac_phase / 720; /* Small modulation */
			u32 noise_seed = (u32)(current_time_ns & 0xFFFFFFFF);
			int env_noise = ((int)(noise_seed % 1000) - 500) * data->temp_generator.noise_level / 1000;
			
			/* Primary heating curve */
			temp_range = data->temp_generator.max_temp - data->temp_generator.min_temp;
			new_temp = data->temp_generator.min_temp + (temp_range * (1000 - exp_factor) / 1000);
			
			/* Add HVAC-like cycling (slow oscillation) */
			new_temp += hvac_effect;
			
			/* Add environmental noise */
			new_temp += env_noise;
		}
		break;
		
	default:
		/* Unknown mode - keep current temperature */
		break;
	}
	
	/* Clamp temperature to reasonable bounds */
	if (new_temp < -40) new_temp = -40;  /* -40°C minimum */
	if (new_temp > 125) new_temp = 125;  /* 125°C maximum */
	
	data->temperature = new_temp;
	
	return new_temp;
}

/**
 * simtemp_update_record - Update temperature record
 */
static void simtemp_update_record(struct nxp_simtemp_data *data)
{
	s32 temp_mC = data->temperature * 1000; /* Convert to mC */
	
	data->record.timestamp_ns = ktime_get_ns(); /* Use monotonic nanoseconds */
	data->record.temp_mC = temp_mC;
	data->record.flags = SIMTEMP_FLAG_NEW_SAMPLE; /* Always set NEW_SAMPLE flag */
	data->record.reserved = 0;
	
	/* Check for threshold crossing and set alert flag */
	if (temp_mC >= (s32)data->threshold_mC) {
		data->record.flags |= SIMTEMP_FLAG_THRESHOLD_CROSSED;
		data->alert_count++;
		dev_info(data->dev, "Alert: temperature %d mC >= threshold %u mC (alert #%u)\n",
			 temp_mC, data->threshold_mC, data->alert_count);
	}
	
	/* F-K4: Signal new sample available and wake waiting processes */
	data->new_sample_available = true;
	wake_up_interruptible(&data->read_wait);
}

/**
 * simtemp_open - Character device open
 */
static int simtemp_open(struct inode *inode, struct file *filp)
{
	struct nxp_simtemp_data *data;
	
	data = container_of(inode->i_cdev, struct nxp_simtemp_data, cdev);
	if (!data)
		return -ENODEV;
	
	mutex_lock(&data->mutex);
	
	if (data->is_open) {
		mutex_unlock(&data->mutex);
		return -EBUSY;
	}
	
	data->is_open = 1;
	filp->private_data = data;
	
	/* F-K2: Start periodic sampling when device opens */
	simtemp_start_sampling(data);
	
	/* Generate initial sample immediately */
	simtemp_generate_temperature(data);
	simtemp_update_record(data);
	
	mutex_unlock(&data->mutex);
	return 0;
}

/**
 * simtemp_release - Character device close
 */
static int simtemp_release(struct inode *inode, struct file *filp)
{
	struct nxp_simtemp_data *data = filp->private_data;
	
	if (!data)
		return -ENODEV;
	
	mutex_lock(&data->mutex);
	data->is_open = 0;
	
	/* F-K2: Stop periodic sampling when device closes */
	simtemp_stop_sampling(data);
	
	mutex_unlock(&data->mutex);
	
	return 0;
}

/**
 * simtemp_read - Character device read (F-K4: supports blocking)
 */
static ssize_t simtemp_read(struct file *filp, char __user *buf,
			    size_t count, loff_t *f_pos)
{
	struct nxp_simtemp_data *data = filp->private_data;
	size_t record_size = sizeof(struct simtemp_record);
	int ret;
	
	if (!data)
		return -ENODEV;
	
	if (count < record_size)
		return -EINVAL;
	
	/* F-K4: Blocking read - wait for new sample unless O_NONBLOCK */
	if (!(filp->f_flags & O_NONBLOCK)) {
		ret = wait_event_interruptible(data->read_wait, 
					       data->new_sample_available);
		if (ret)
			return ret; /* Interrupted by signal */
	} else {
		/* Non-blocking: return immediately if no data */
		if (!data->new_sample_available)
			return -EAGAIN;
	}
	
	mutex_lock(&data->mutex);
	
	/* Clear the flag since we're consuming the sample */
	data->new_sample_available = false;
	
	if (copy_to_user(buf, &data->record, record_size)) {
		mutex_unlock(&data->mutex);
		return -EFAULT;
	}
	mutex_unlock(&data->mutex);
	
	return record_size;
}

/**
 * simtemp_poll - F-K4: Poll/epoll support
 */
static __poll_t simtemp_poll(struct file *filp, poll_table *wait)
{
	struct nxp_simtemp_data *data = filp->private_data;
	__poll_t mask = 0;
	
	if (!data)
		return EPOLLERR;
	
	/* Add to wait queue for poll/epoll */
	poll_wait(filp, &data->read_wait, wait);
	
	/* Check if data is available */
	if (data->new_sample_available)
		mask |= EPOLLIN | EPOLLRDNORM; /* Data ready for reading */
	
	/* Always ready for writing (not implemented but good practice) */
	mask |= EPOLLOUT | EPOLLWRNORM;
	
	return mask;
}

/**
 * simtemp_ioctl - F-K7: ioctl support for configuration
 */
static long simtemp_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	struct nxp_simtemp_data *data = filp->private_data;
	u32 value;
	int ret = 0;
	
	if (!data)
		return -ENODEV;
	
	/* Verify ioctl magic number */
	if (_IOC_TYPE(cmd) != SIMTEMP_IOC_MAGIC)
		return -ENOTTY;
	
	/* Verify ioctl command number */
	if (_IOC_NR(cmd) > SIMTEMP_IOC_MAXNR)
		return -ENOTTY;
	
	switch (cmd) {
	case SIMTEMP_IOC_GET_SAMPLING:
		mutex_lock(&data->mutex);
		value = data->sampling_ms;
		mutex_unlock(&data->mutex);
		
		if (copy_to_user((u32 __user *)arg, &value, sizeof(u32)))
			return -EFAULT;
		break;
		
	case SIMTEMP_IOC_SET_SAMPLING:
		if (copy_from_user(&value, (u32 __user *)arg, sizeof(u32)))
			return -EFAULT;
		
		/* Validate range: 100ms to 10s */
		if (value < 100 || value > 10000) {
			dev_warn(data->dev, "Invalid sampling_ms %u (valid: 100-10000)\n", value);
			return -EINVAL;
		}
		
		mutex_lock(&data->mutex);
		data->sampling_ms = value;
		
		/* Restart timer with new interval if active */
		if (data->timer_active) {
			del_timer_sync(&data->sample_timer);
			mod_timer(&data->sample_timer,
				  jiffies + msecs_to_jiffies(data->sampling_ms));
		}
		mutex_unlock(&data->mutex);
		
		dev_info(data->dev, "ioctl: Updated sampling interval to %u ms\n", value);
		break;
		
	case SIMTEMP_IOC_GET_THRESHOLD:
		mutex_lock(&data->mutex);
		value = data->threshold_mC;
		mutex_unlock(&data->mutex);
		
		if (copy_to_user((u32 __user *)arg, &value, sizeof(u32)))
			return -EFAULT;
		break;
		
	case SIMTEMP_IOC_SET_THRESHOLD:
		if (copy_from_user(&value, (u32 __user *)arg, sizeof(u32)))
			return -EFAULT;
		
		/* Validate range: 0°C to 125°C in mC */
		if (value > 125000) {
			dev_warn(data->dev, "Invalid threshold_mC %u (valid: 0-125000)\n", value);
			return -EINVAL;
		}
		
		mutex_lock(&data->mutex);
		data->threshold_mC = value;
		mutex_unlock(&data->mutex);
		
		dev_info(data->dev, "ioctl: Updated threshold to %u mC (%u.%03u°C)\n", 
			 value, value / 1000, value % 1000);
		break;
		
	default:
		return -ENOTTY;
	}
	
	return ret;
}

/* Character device file operations */
static const struct file_operations simtemp_fops = {
	.owner = THIS_MODULE,
	.open = simtemp_open,
	.release = simtemp_release,
	.read = simtemp_read,
	.poll = simtemp_poll,
	.unlocked_ioctl = simtemp_ioctl,
};

/**
 * simtemp_create_chardev - Create character device
 */
static int simtemp_create_chardev(struct nxp_simtemp_data *data)
{
	int ret;
	
	/* Initialize character device */
	cdev_init(&data->cdev, &simtemp_fops);
	data->cdev.owner = THIS_MODULE;
	
	/* Add character device */
	ret = cdev_add(&data->cdev, data->devt, 1);
	if (ret) {
		dev_err(data->dev, "Failed to add cdev: %d\n", ret);
		return ret;
	}
	
	/* Create device node */
	data->device = device_create(simtemp_class, data->dev,
				     data->devt, data, DEVICE_NAME "%d",
				     MINOR(data->devt));
	if (IS_ERR(data->device)) {
		ret = PTR_ERR(data->device);
		dev_err(data->dev, "Failed to create device: %d\n", ret);
		cdev_del(&data->cdev);
		return ret;
	}

	/* Link private data to class device for sysfs handlers */
	dev_set_drvdata(data->device, data);

	/* Expose key attributes on the class device (under /sys/class/simtemp_class) */
	ret = device_create_file(data->device, &dev_attr_sampling_ms);
	if (ret) {
		dev_warn(data->dev, "Could not create sampling_ms attribute on class device: %d\n", ret);
	}
	ret = device_create_file(data->device, &dev_attr_threshold_mC);
	if (ret) {
		dev_warn(data->dev, "Could not create threshold_mC attribute on class device: %d\n", ret);
	}
	ret = device_create_file(data->device, &dev_attr_mode);
	if (ret) {
		dev_warn(data->dev, "Could not create mode attribute on class device: %d\n", ret);
	}
	ret = device_create_file(data->device, &dev_attr_stats);
	if (ret) {
		dev_warn(data->dev, "Could not create stats attribute on class device: %d\n", ret);
	}
	
	return 0;
}

/**
 * simtemp_destroy_chardev - Destroy character device
 */
static void simtemp_destroy_chardev(struct nxp_simtemp_data *data)
{
	if (data->device) {
		/* Remove class device attributes if present */
		device_remove_file(data->device, &dev_attr_stats);
		device_remove_file(data->device, &dev_attr_mode);
		device_remove_file(data->device, &dev_attr_threshold_mC);
		device_remove_file(data->device, &dev_attr_sampling_ms);
		device_destroy(simtemp_class, data->devt);
		data->device = NULL;
	}
	
	cdev_del(&data->cdev);
}

/**
 * nxp_simtemp_probe - Platform driver probe function
 * @pdev: Platform device
 *
 * Return: 0 on success, negative error code on failure
 */
static int nxp_simtemp_probe(struct platform_device *pdev)
{
	struct nxp_simtemp_data *data;
	struct device *dev = &pdev->dev;
	const char *mode;
	int ret;

	dev_info(dev, "NXP SimTemp probe starting for device %s\n", dev_name(dev));

	/* Allocate device data */
	data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
	if (!data) {
		dev_err(dev, "Failed to allocate device data\n");
		return -ENOMEM;
	}

	/* Initialize data */
	data->dev = dev;
	data->pdev = pdev;
	data->temperature = 25;
	data->is_open = 0;
	mutex_init(&data->mutex);

	/* F-K2: Initialize sampling timer */
	timer_setup(&data->sample_timer, simtemp_timer_callback, 0);
	data->timer_active = false;

	/* F-K4: Initialize wait queue for blocking read/poll */
	init_waitqueue_head(&data->read_wait);
	data->new_sample_available = false;

	/* Initialize temperature generator with default linear ramp */
	data->temp_generator.pattern_type = SIMTEMP_MODE_LINEAR;
	data->temp_generator.sample_count = 0;
	data->temp_generator.start_time_ms = 0;
	data->temp_generator.base_temperature = 25;  /* 25°C base */
	data->temp_generator.min_temp = 20;          /* 20°C minimum */
	data->temp_generator.max_temp = 80;          /* 80°C maximum */
	data->temp_generator.period_ms = 60000;      /* 60 second period */
	data->temp_generator.amplitude = 5;          /* ±5°C amplitude for sine/noise */
	data->temp_generator.noise_level = 500;      /* 0.5°C noise level (milli-degrees) */
	data->temp_generator.enabled = true;         /* Enable by default */

	/* Allocate device number */
	data->devt = MKDEV(MAJOR(simtemp_devt), device_count++);

	/* Set defaults */
	data->sampling_ms = 1000;	// To be overridden by device properties in DT
	data->threshold_mC = 50000;	// To be overridden by device properties in DT
	data->mode = "default";
	data->alert_count = 0;

	/* Read device properties */
	device_property_read_u32(dev, "sampling-ms", &data->sampling_ms);
	device_property_read_u32(dev, "threshold-mC", &data->threshold_mC);
	if (!device_property_read_string(dev, "mode", &mode))
		data->mode = mode;

	/* Validate values */
	if (data->sampling_ms < 100 || data->sampling_ms > 10000) {
		dev_warn(dev, "Invalid sampling-ms %u, using default 1000\n", data->sampling_ms);
		data->sampling_ms = 1000;
	}

	if (data->threshold_mC > 125000) {
		dev_warn(dev, "Invalid threshold-mC %u, using default 50000\n", data->threshold_mC);
		data->threshold_mC = 50000;
	}

	/* Set driver data */
	platform_set_drvdata(pdev, data);

	/* Create sysfs attributes */
	ret = devm_device_add_group(dev, &nxp_simtemp_group);
	if (ret) {
		dev_err(dev, "Failed to create sysfs attributes: %d\n", ret);
		platform_set_drvdata(pdev, NULL);
		return ret;
	}

	/* Create character device */
	ret = simtemp_create_chardev(data);
	if (ret) {
		dev_err(dev, "Failed to create character device: %d\n", ret);
		platform_set_drvdata(pdev, NULL);
		return ret;
	}

	dev_info(dev, "Probe completed: sampling_ms=%u threshold_mC=%u mode=%s\n",
		 data->sampling_ms, data->threshold_mC, data->mode);
	dev_info(dev, "Character device created: /dev/simtemp%d\n", 
		 MINOR(data->devt));
	return 0;
}

/**
 * nxp_simtemp_remove - Platform driver remove function
 */
static void nxp_simtemp_remove(struct platform_device *pdev)
{
	struct nxp_simtemp_data *data = platform_get_drvdata(pdev);
	struct device *dev = &pdev->dev;

	dev_info(dev, "NXP SimTemp remove starting for device %s\n", dev_name(dev));

	if (!data) {
		dev_warn(dev, "No device data found during remove\n");
		return;
	}

	/* F-K2: Stop and cleanup timer */
	simtemp_stop_sampling(data);

	/* Destroy character device */
	simtemp_destroy_chardev(data);

	/* Clear driver data */
	platform_set_drvdata(pdev, NULL);

	dev_info(dev, "NXP SimTemp remove completed successfully\n");
}

/**
 * Device Tree compatible strings
 */
static const struct of_device_id nxp_simtemp_of_match[] = {
	{ .compatible = "nxp,simtemp" },
	{ .compatible = "simtemp,temperature-sensor" },
	{ .compatible = "simtemp,temperature-sensor-overlay" },
	{ /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, nxp_simtemp_of_match);

static const struct platform_device_id nxp_simtemp_id[] = {
	{ "nxp-simtemp", 0 },
	{ /* sentinel */ }
};
MODULE_DEVICE_TABLE(platform, nxp_simtemp_id);

/**
 * Platform driver structure
 */
static struct platform_driver nxp_simtemp_driver = {
	.probe = nxp_simtemp_probe,
	.remove = nxp_simtemp_remove,
	.driver = {
		.name = "nxp-simtemp",
#ifdef CONFIG_OF
		.of_match_table = nxp_simtemp_of_match,
#endif
		.groups = nxp_simtemp_groups,
	},
	.id_table = nxp_simtemp_id, /* key for non-DT */
};

static int __init nxp_simtemp_init(void)
{
	int ret;

	pr_info("NXP SimTemp driver: Initializing (version %s)\n", "1.0.0");

#ifdef CONFIG_X86
	/* On x86, recommend loading stub for testing */
	pr_info("NXP SimTemp driver: x86 detected - consider loading nxp_simtemp_stub for testing\n");
#endif

	/* Allocate character device numbers */
	ret = alloc_chrdev_region(&simtemp_devt, 0, 4, DEVICE_NAME);
	if (ret) {
		pr_err("NXP SimTemp driver: Failed to allocate device numbers: %d\n", ret);
		goto err_chrdev_alloc;
	}

	/* Create device class */
	simtemp_class = class_create(CLASS_NAME);
	if (IS_ERR(simtemp_class)) {
		ret = PTR_ERR(simtemp_class);
		pr_err("NXP SimTemp driver: Failed to create class: %d\n", ret);
		goto err_class_create;
	}

	/* Register platform driver */
	ret = platform_driver_register(&nxp_simtemp_driver);
	if (ret) {
		pr_err("NXP SimTemp driver: Failed to register platform driver: %d\n", ret);
		goto err_driver_register;
	}

	pr_info("NXP SimTemp driver: Initialized successfully\n");
	return 0;

err_driver_register:
	class_destroy(simtemp_class);
err_class_create:
	unregister_chrdev_region(simtemp_devt, 4);
err_chrdev_alloc:
	pr_err("NXP SimTemp driver: Initialization failed with error %d\n", ret);
	return ret;
}

static void __exit nxp_simtemp_exit(void)
{
	pr_info("NXP SimTemp driver: Initiating cleanup\n");
	
	/* Unregister platform driver */
	platform_driver_unregister(&nxp_simtemp_driver);
	
	/* Destroy device class */
	class_destroy(simtemp_class);
	
	/* Release character device numbers */
	unregister_chrdev_region(simtemp_devt, 4);
	
	pr_info("NXP SimTemp driver: Cleanup completed\n");
}

module_init(nxp_simtemp_init);
module_exit(nxp_simtemp_exit);

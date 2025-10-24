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
 * struct simtemp_record - Binary temperature record
 * @timestamp: Timestamp in jiffies
 * @temperature: Temperature in milliCelsius
 * @status: Status flags
 * @reserved: Reserved for future use
 */
struct simtemp_record {
	u64 timestamp;
	s32 temperature;
	u32 status;
	u32 reserved;
};

/**
 * struct nxp_simtemp_data - Private data structure
 * @dev: Device pointer
 * @pdev: Platform device pointer
 * @cdev: Character device
 * @device: Device class device
 * @class: Device class
 * @devt: Device number
 * @mutex: Mutex for thread safety
 * @temperature: Current simulated temperature
 * @sampling_ms: Sampling interval in milliseconds
 * @threshold_mC: Temperature threshold in milliCelsius
 * @mode: Operating mode string
 * @is_open: Device open flag
 * @record: Current temperature record
 */
struct nxp_simtemp_data {
	struct device *dev;
	struct platform_device *pdev;
	struct cdev cdev;
	struct device *device;
	struct class *class;
	dev_t devt;
	struct mutex mutex;
	int temperature;
	u32 sampling_ms;
	u32 threshold_mC;
	const char *mode;
	int is_open;
	struct simtemp_record record;
};

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

/* Define device attributes */
static DEVICE_ATTR_RO(sampling_ms);
static DEVICE_ATTR_RO(threshold_mC);
static DEVICE_ATTR_RO(mode);

/* Attribute group */
static struct attribute *nxp_simtemp_attrs[] = {
	&dev_attr_sampling_ms.attr,
	&dev_attr_threshold_mC.attr,
	&dev_attr_mode.attr,
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
 * simtemp_update_record - Update temperature record
 */
static void simtemp_update_record(struct nxp_simtemp_data *data)
{
	data->record.timestamp = get_jiffies_64();
	data->record.temperature = data->temperature * 1000; /* Convert to mC */
	data->record.status = 0; /* Normal status */
	data->record.reserved = 0;
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
	mutex_unlock(&data->mutex);
	
	return 0;
}

/**
 * simtemp_read - Character device read
 */
static ssize_t simtemp_read(struct file *filp, char __user *buf,
			    size_t count, loff_t *f_pos)
{
	struct nxp_simtemp_data *data = filp->private_data;
	size_t record_size = sizeof(struct simtemp_record);
	
	if (!data)
		return -ENODEV;
	
	/* Non-blocking read when no data available */
	if (filp->f_flags & O_NONBLOCK)
		return -EAGAIN;
	
	if (count < record_size)
		return -EINVAL;
	
	mutex_lock(&data->mutex);
	simtemp_update_record(data);
	
	if (copy_to_user(buf, &data->record, record_size)) {
		mutex_unlock(&data->mutex);
		return -EFAULT;
	}
	
	mutex_unlock(&data->mutex);
	return record_size;
}

/* Character device file operations */
static const struct file_operations simtemp_fops = {
	.owner = THIS_MODULE,
	.open = simtemp_open,
	.release = simtemp_release,
	.read = simtemp_read,
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
	
	return 0;
}

/**
 * simtemp_destroy_chardev - Destroy character device
 */
static void simtemp_destroy_chardev(struct nxp_simtemp_data *data)
{
	if (data->device) {
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

	/* Allocate device number */
	data->devt = MKDEV(MAJOR(simtemp_devt), device_count++);

	/* Set defaults */
	data->sampling_ms = 1000;
	data->threshold_mC = 50000;
	data->mode = "default";

	/* Read device properties */
	device_property_read_u32(dev, "sampling-ms", &data->sampling_ms);
	device_property_read_u32(dev, "threshold-microc", &data->threshold_mC);
	if (!device_property_read_string(dev, "mode", &mode))
		data->mode = mode;

	/* Validate values */
	if (data->sampling_ms < 100 || data->sampling_ms > 10000) {
		dev_warn(dev, "Invalid sampling-ms %u, using default 1000\n", data->sampling_ms);
		data->sampling_ms = 1000;
	}

	if (data->threshold_mC < -40000 || data->threshold_mC > 125000) {
		dev_warn(dev, "Invalid threshold-microc %u, using default 50000\n", data->threshold_mC);
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

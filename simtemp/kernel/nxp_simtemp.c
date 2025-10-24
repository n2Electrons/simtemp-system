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

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Jorge Rodriguez Moreno");
MODULE_DESCRIPTION("Temperature Simulator Driver with Clean Load/Unload Support");
MODULE_VERSION("1.0.0");

/* For x86 systems without Device Tree, request the stub module */
#ifdef CONFIG_X86
MODULE_SOFTDEP("pre: nxp_simtemp_stub");
#endif

#define DRIVER_NAME "nxp-simtemp"

/**
 * struct nxp_simtemp_data - Private data structure
 * @dev: Device pointer
 * @temperature: Current simulated temperature
 * @sampling_ms: Sampling interval in milliseconds
 * @threshold_mC: Temperature threshold in milliCelsius
 * @mode: Operating mode string
 */
struct nxp_simtemp_data {
	struct device *dev;
	int temperature;
	u32 sampling_ms;
	u32 threshold_mC;
	const char *mode;
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
	data->temperature = 25;

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
		/* Cleanup on failure */
		platform_set_drvdata(pdev, NULL);
		return ret;
	}

	dev_info(dev, "Probe completed successfully: sampling_ms=%u threshold_mC=%u mode=%s\n",
		 data->sampling_ms, data->threshold_mC, data->mode);
	return 0;
}

/**
 * nxp_simtemp_remove - Platform driver remove function
 * @pdev: Platform device being removed
 *
 * Implements proper cleanup for graceful unload.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 11, 0)
static void nxp_simtemp_remove(struct platform_device *pdev)
{
	struct nxp_simtemp_data *data = platform_get_drvdata(pdev);
	struct device *dev = &pdev->dev;

	dev_info(dev, "NXP SimTemp remove starting for device %s\n", dev_name(dev));

	/* Verify data */
	if (!data) {
		dev_warn(dev, "No device data found during remove\n");
		return;
	}

	/* 
	 * Cleanup is automatic via devm_ functions
	 */

	/* Clear driver data */
	platform_set_drvdata(pdev, NULL);

	dev_info(dev, "NXP SimTemp remove completed successfully\n");
}
#else
static int nxp_simtemp_remove(struct platform_device *pdev)
{
	struct nxp_simtemp_data *data = platform_get_drvdata(pdev);
	struct device *dev = &pdev->dev;

	dev_info(dev, "NXP SimTemp remove starting for device %s\n", dev_name(dev));

	/* Verify data */
	if (!data) {
		dev_warn(dev, "No device data found during remove\n");
		return 0;
	}

	/* 
	 * Cleanup is automatic via devm_ functions
	 */

	/* Clear driver data */
	platform_set_drvdata(pdev, NULL);

	dev_info(dev, "NXP SimTemp remove completed successfully\n");
	return 0;
}
#endif

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

	/* Register platform driver */
	ret = platform_driver_register(&nxp_simtemp_driver);
	if (ret) {
		pr_err("NXP SimTemp driver: Failed to register platform driver: %d\n", ret);
		goto err_driver_register;
	}

	pr_info("NXP SimTemp driver: Platform driver registered successfully\n");
	return 0;

err_driver_register:
	pr_err("NXP SimTemp driver: Initialization failed with error %d\n", ret);
	return ret;
}

static void __exit nxp_simtemp_exit(void)
{
	pr_info("NXP SimTemp driver: Initiating cleanup\n");
	
	/* Unregister driver - triggers remove() for all devices */
	platform_driver_unregister(&nxp_simtemp_driver);
	
	/* Brief pause for cleanup completion */
	msleep(10);
	
	pr_info("NXP SimTemp driver: Cleanup completed\n");
}

module_init(nxp_simtemp_init);
module_exit(nxp_simtemp_exit);

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

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Jorge Rodriguez Moreno");
MODULE_DESCRIPTION("Temperature Simulator Driver");

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
 * Sysfs attribute show functions for DTB properties
 */
static ssize_t sampling_ms_show(struct device *dev,
				struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	return sprintf(buf, "%u\n", data->sampling_ms);
}

static ssize_t threshold_mC_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
	return sprintf(buf, "%u\n", data->threshold_mC);
}

static ssize_t mode_show(struct device *dev,
			 struct device_attribute *attr, char *buf)
{
	struct nxp_simtemp_data *data = dev_get_drvdata(dev);
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
 * This function is called when a device matching our compatible string
 * is found in the device tree.
 *
 * Return: 0 on success, negative error code on failure
 */
static int nxp_simtemp_probe(struct platform_device *pdev)
{
	struct nxp_simtemp_data *data;
	struct device *dev = &pdev->dev;
	const char *mode;
	int ret;

	dev_info(dev, "NXP SimTemp probe start\n");

	data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;

	data->dev = dev;
	data->temperature = 25;

	/* Defaults */
	data->sampling_ms = 1000;
	data->threshold_mC = 50000;
	data->mode = "default";

	/* Works with DT/ACPI/software node; if nothing present, keeps defaults */
	device_property_read_u32(dev, "sampling-ms", &data->sampling_ms);
	device_property_read_u32(dev, "threshold-microc", &data->threshold_mC);
	if (!device_property_read_string(dev, "mode", &mode))
		data->mode = mode;

	platform_set_drvdata(pdev, data);

	/* Sysfs with automatic management and implicit cleanup */
	ret = devm_device_add_group(dev, &nxp_simtemp_group);
	if (ret) {
		dev_err(dev, "sysfs groups failed: %d\n", ret);
		return ret;
	}

	dev_info(dev, "probe ok: sampling_ms=%u threshold_mC=%u mode=%s\n",
		 data->sampling_ms, data->threshold_mC, data->mode);
	return 0;
}

/**
 * nxp_simtemp_remove - Platform driver remove function
 * @pdev: Platform device
 *
 * This function is called when the device is removed or the driver
 * is unloaded.
 * 
 * Note: Return type varies by kernel version - void for older kernels,
 * int for newer kernels. We use a wrapper approach for compatibility.
 */
static void nxp_simtemp_remove(struct platform_device *pdev)
{
	/* Nothing needed if using devm_device_add_group */
	dev_info(&pdev->dev, "NXP SimTemp driver remove called\n");
}

/**
 * Device Tree compatible strings
 * Match entries dtb
 * Trigger the probe function when found.
 */
static const struct of_device_id nxp_simtemp_of_match[] = {
	{ .compatible = "nxp,simtemp" },
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
 * Associates it with dtbstrings.
 */
static struct platform_driver nxp_simtemp_driver = {
	.probe = nxp_simtemp_probe,
	.remove = nxp_simtemp_remove,
	.driver = {
		.name = "nxp-simtemp",
#ifdef CONFIG_OF
		.of_match_table = nxp_simtemp_of_match,
#endif
	},
	.id_table = nxp_simtemp_id, /* key for non-DT */
};
module_platform_driver(nxp_simtemp_driver);

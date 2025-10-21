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

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Jorge Rodriguez Moreno");
MODULE_DESCRIPTION("Temperature Simulator Driver");

#define DRIVER_NAME "nxp-simtemp"

/**
 * struct nxp_simtemp_data - Private data structure
 * @dev: Device pointer
 * @temperature: Current simulated temperature
 */
struct nxp_simtemp_data {
	struct device *dev;
	int temperature;
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

	dev_info(dev, "NXP SimTemp driver probe started\n");

	/* Allocate private data structure */
	data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;

	data->dev = dev;
	data->temperature = 25; /* Default temperature */

	/* Store private data in platform device */
	platform_set_drvdata(pdev, data);

	dev_info(dev, "NXP SimTemp driver probe completed successfully\n");

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
static void nxp_simtemp_remove_impl(struct platform_device *pdev)
{
	dev_info(&pdev->dev, "NXP SimTemp driver remove called\n");

	/* Private data is automatically freed by devm_kzalloc */
}

/* Kernel version compatibility wrapper - arm kernels expect int, x86 kernels expect void */
#ifdef CONFIG_ARM
static int nxp_simtemp_remove(struct platform_device *pdev)
{
	nxp_simtemp_remove_impl(pdev);
	return 0;
}
#else
static void nxp_simtemp_remove(struct platform_device *pdev)
{
	nxp_simtemp_remove_impl(pdev);
    return;
}
#endif

/**
 * Device Tree compatible strings
 * Match entries dtb
 * Trigger the probe function when found.
 */
static const struct of_device_id nxp_simtemp_of_match[] = {
	{
		.compatible = "simtemp,temperature-sensor",
	},
	{
		.compatible = "simtemp,temperature-sensor-overlay",
	},
	{ }
};
MODULE_DEVICE_TABLE(of, nxp_simtemp_of_match);

/**
 * Platform driver structure
 * Associates it with dtbstrings.
 */
static struct platform_driver nxp_simtemp_driver = {
	.probe = nxp_simtemp_probe,
	.remove = nxp_simtemp_remove,
	.driver = {
		.name = DRIVER_NAME,
		.of_match_table = nxp_simtemp_of_match,
	},
};

// nxp_simtemp_init
static int __init nxp_simtemp_init(void)
{
	int ret;

	pr_info("NXP SimTemp driver: Initializing\n");

	ret = platform_driver_register(&nxp_simtemp_driver);
	if (ret) {
		pr_err("NXP SimTemp driver: Failed to register platform driver: %d\n", ret);
		return ret;
	}

	pr_info("NXP SimTemp driver: Platform driver registered successfully\n");
	return 0;
}

//nxp_simtemp_exit
static void __exit nxp_simtemp_exit(void)
{
	pr_info("NXP SimTemp driver: Cleaning up\n");
	platform_driver_unregister(&nxp_simtemp_driver);
	pr_info("NXP SimTemp driver: Platform driver unregistered\n");
}

module_init(nxp_simtemp_init);
module_exit(nxp_simtemp_exit);

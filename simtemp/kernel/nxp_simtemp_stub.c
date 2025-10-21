// SPDX-License-Identifier: GPL-2.0+
/*
 * NXP SimTemp Stub Driver - Creates platform device for testing
 * This module creates a platform device with software node properties
 * for testing the nxp_simtemp driver on non-DT systems (like x86_64)
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 */

#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/property.h>

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Jorge Rodriguez Moreno");
MODULE_DESCRIPTION("NXP SimTemp Stub Driver for Testing");

/* This module provides test devices for the nxp_simtemp driver on x86 */
MODULE_SOFTDEP("post: nxp_simtemp");

static const struct property_entry simtemp_props[] = {
	PROPERTY_ENTRY_U32("sampling-ms", 200),
	PROPERTY_ENTRY_U32("threshold-microc", 60000),
	PROPERTY_ENTRY_STRING("mode", "lab"),
	{ }
};

static struct software_node simtemp_swnode = {
	.name = "nxp-simtemp.swnode",
	.properties = simtemp_props,
};

static struct platform_device *pdev;

static int __init nxp_simtemp_stub_init(void)
{
	int ret;

	pr_info("nxp_simtemp_stub: Initializing test device provider\n");
	pr_info("nxp_simtemp_stub: Creating simulated DTB device for nxp_simtemp driver\n");

	ret = software_node_register(&simtemp_swnode);
	if (ret) {
		pr_err("nxp_simtemp_stub: Failed to register software node: %d\n", ret);
		return ret;
	}

	pdev = platform_device_alloc("nxp-simtemp", PLATFORM_DEVID_AUTO);
	if (!pdev) {
		pr_err("nxp_simtemp_stub: Failed to allocate platform device\n");
		software_node_unregister(&simtemp_swnode);
		return -ENOMEM;
	}

	ret = device_add_software_node(&pdev->dev, &simtemp_swnode);
	if (ret) {
		pr_err("nxp_simtemp_stub: Failed to add software node: %d\n", ret);
		platform_device_put(pdev);
		software_node_unregister(&simtemp_swnode);
		return ret;
	}

	ret = platform_device_add(pdev);
	if (ret) {
		pr_err("nxp_simtemp_stub: Failed to add platform device: %d\n", ret);
		device_remove_software_node(&pdev->dev);
		platform_device_put(pdev);
		software_node_unregister(&simtemp_swnode);
		return ret;
	}

	pr_info("nxp_simtemp_stub: Platform device registered with software node\n");
	return 0;
}

static void __exit nxp_simtemp_stub_exit(void)
{
	pr_info("nxp_simtemp_stub: Cleaning up\n");

	if (pdev) {
		device_remove_software_node(&pdev->dev);
		platform_device_unregister(pdev);
	}
	software_node_unregister(&simtemp_swnode);

	pr_info("nxp_simtemp_stub: Unregistered\n");
}

module_init(nxp_simtemp_stub_init);
module_exit(nxp_simtemp_stub_exit);
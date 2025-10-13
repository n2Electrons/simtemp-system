// SPDX-License-Identifier: GPL-2.0+
/*
 *  Temperature Simulator Driver
 *
 * Copyright (c) 2025 Jorge Rodriguez Moreno
 */

#include <linux/module.h>
#include <linux/platform_device.h>

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Jorge Rodriguez Moreno");
MODULE_DESCRIPTION("Temperature Simulator Driver");

/* Empty driver - TDD Phase 1: Test should fail */
static int __init nxp_simtemp_init(void)
{
    return 0;
}

static void __exit nxp_simtemp_exit(void)
{
}

module_init(nxp_simtemp_init);
module_exit(nxp_simtemp_exit);

# DevTree_in_x86_64_STUB.md

## Objective
Provide a development and testing method for Linux platform drivers on **x86_64** hosts when the final deployment target (e.g., **i.MX6**) uses a **Device Tree (DT)**.  
This allows driver verification without actual DT hardware by registering a synthetic `platform_device`.

---

## 1. Concept Overview

In DT-based systems (ARM, PowerPC, etc.), devices are instantiated automatically by parsing the **Device Tree Blob (DTB)**.  
On x86_64, the kernel usually lacks a DT, so drivers using `.of_match_table` won’t get probed.  
To test such drivers, you can **manually register a `platform_device`** and optionally attach **software nodes** to simulate DT properties.

---

## 2. Minimal Driver Structure

The driver must support both DT and non-DT paths:

```c
static const struct of_device_id nxp_simtemp_of_match[] = {
    { .compatible = "nxp,simtemp" }, { }
};
MODULE_DEVICE_TABLE(of, nxp_simtemp_of_match);

static const struct platform_device_id nxp_simtemp_id[] = {
    { "nxp-simtemp", 0 }, { }
};
MODULE_DEVICE_TABLE(platform, nxp_simtemp_id);

static int nxp_simtemp_probe(struct platform_device *pdev)
{
    struct nxp_simtemp_data *data;
    struct device *dev = &pdev->dev;
    const char *mode;
    int ret;

    data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    data->sampling_ms = 1000;
    data->threshold_mC = 50000;
    data->mode = "default";

    device_property_read_u32(dev, "sampling-ms", &data->sampling_ms);
    device_property_read_u32(dev, "threshold-microc", &data->threshold_mC);
    if (!device_property_read_string(dev, "mode", &mode))
        data->mode = mode;

    platform_set_drvdata(pdev, data);
    ret = devm_device_add_groups(dev, nxp_simtemp_groups);
    if (ret)
        return ret;

    dev_info(dev, "probe ok: sampling_ms=%u threshold_mC=%u mode=%s\n",
             data->sampling_ms, data->threshold_mC, data->mode);
    return 0;
}
```

---

## 3. Stub Device Registration

### Option A: Basic Registration
```c
static int __init stub_init(void)
{
    struct platform_device *pdev;
    pdev = platform_device_register_simple("nxp-simtemp", -1, NULL, 0);
    return PTR_ERR_OR_ZERO(pdev);
}
```

### Option B: Software Node with Properties
```c
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
```
This lets the driver read “virtual DT properties” via the unified property API.

---

## 4. Test Sequence

```bash
modprobe nxp_simtemp
insmod nxp_simtemp_stub.ko
dmesg | grep -i simtemp
ls /sys/bus/platform/devices | grep -i simtemp
cat /sys/bus/platform/devices/*simtemp*/sampling_ms
```

---

## 5. Migration to i.MX6

When moving to the embedded target:
- Remove the stub module.
- Add a node in the `.dts` file:
  ```dts
  simtemp@0 {
      compatible = "nxp,simtemp";
      sampling-ms = <1000>;
      threshold-microc = <50000>;
      mode = "default";
  };
  ```
- Reuse the same driver source without modification.

---

## 6. References

1. **Platform Devices and Drivers**  
   [docs.kernel.org/driver-api/driver-model/platform.html](https://docs.kernel.org/driver-api/driver-model/platform.html)

2. **platform_device_register_simple() Manual**  
   [manpages.debian.org/jessie/linux-manual-3.16/platform_device_register_simple.9](https://manpages.debian.org/jessie/linux-manual-3.16/platform_device_register_simple.9)

3. **Platform Devices and Device Trees** — LWN.net  
   [https://lwn.net/Articles/448502/](https://lwn.net/Articles/448502/)

4. **Unified Device Properties API** — Linux Foundation presentation  
   [Unified Properties API PDF](https://events.static.linuxfound.org/sites/events/files/slides/unified_properties_API_0.pdf)

---

**Purpose:** enable DT-based driver validation on non-DT hosts while keeping code portable and production-ready.

# QEMU i.MX6 Boot Hang Troubleshooting

## 1. Symptom

Boot output stops after lines such as:
```
[   11.159482] i2c /dev entries driver
[   11.173667] mxc_v4l2_output v4l2_out: V4L2 device registered as video16
[   11.174567] mxc_v4l2_output v4l2_out: V4L2 device registered as video17
...
```
System appears frozen.

---

## 2. Root Cause

Not an actual kernel freeze.  
QEMU emulates limited hardware. Drivers like **IPU**, **VPU**, and **HDMI** wait on non-existent devices, blocking boot.

---

## 3. Recommended Kernel Command Line

Use proper serial console and disable display/video subsystems:

```bash
console=ttymxc0,115200 earlycon=ec_imx6q,0x02020000 ignore_loglevel initcall_debug printk.time=1 modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore
```

Add to your QEMU run command’s `-append` section.

---

## 4. Example QEMU Command

```bash
qemu-system-arm -M sabrelite -cpu cortex-a9 -m 1024   -nographic -serial mon:stdio   -kernel zImage -dtb imx6q-sabrelite.dtb -initrd initramfs.cpio.gz   -append 'console=ttymxc0,115200 earlycon=ec_imx6q,0x02020000            ignore_loglevel initcall_debug printk.time=1            modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore'
```

---

## 5. Additional Diagnostic Options

| Command | Description |
|----------|-------------|
| `echo t > /proc/sysrq-trigger` | Dumps running tasks to dmesg (detect hangs). |
| `initcall_debug` | Prints duration of each driver initialization. |
| `clk_ignore_unused` | Prevents clock gating issues during probe. |
| `systemd.mask=systemd-random-seed.service` | Avoids long waits on some rootfs images. |

---

## 6. Common Mistakes

- Using wrong console (`ttyAMA0`) instead of `ttymxc0`.  
- Missing or misdeclared rootfs (`root=/dev/ram0` for initramfs).  
- Leaving IPU/VPU/HDMI enabled in the DTS file.  
- Forgetting pull-ups on I²C (in hardware runs).

---

## 7. Quick Fix Summary

| Case | Fix |
|------|-----|
| QEMU without display | Blacklist video drivers (see above). |
| Real hardware | Keep video nodes enabled. Ensure display power and clocks are valid. |
| Still hangs | Use `initcall_debug` and dump tasks. Check last driver init message. |

---

## 8. References

- NXP i.MX6 Reference Manual (I2C, IPU, VPU sections)  
- QEMU ARM Machine “sabrelite” source (`hw/arm/fsl-imx6.c`)  
- Linux kernel docs: *initcall_debug*, *modprobe.blacklist*, *earlycon*

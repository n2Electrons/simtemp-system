# SENSOR-TO-QEMU-SERIAL.md

## ✅ Solution 1: Add a Second Serial Backend in QEMU

If you want to simulate communication with a sensor or external device connected to a second UART (e.g., `/dev/ttymxc1`) in your QEMU-emulated i.MX6 system, you must explicitly connect that UART to a backend in QEMU.

### 🔍 Problem
If you try to write to `/dev/ttymxc1` in Linux without QEMU attaching anything to it, the kernel may panic or crash because there is no valid emulation or backing for that UART's memory-mapped IO (MMIO).

### ✅ QEMU Setup with Second Serial Channel

Here's how to run QEMU with a second UART channel connected via a TCP socket:

```bash
qemu-system-arm -M sabrelite \
  -cpu cortex-a9 \
  -m 1024 -nographic -no-reboot \
  -kernel zImage \
  -dtb imx6q-sabrelite.dtb \
  -initrd rootfs.cpio.gz \
  -append "console=ttymxc0,115200 rdinit=/init" \
  -serial stdio \
  -chardev socket,id=mysensor,server=on,host=127.0.0.1,port=4444,wait=off \
  -serial chardev:mysensor
```

This command does the following:

- `-serial stdio`: Maps the main console (`/dev/ttymxc0`) to your terminal.
- `-chardev socket,...`: Creates a TCP socket listener on port 4444.
- `-serial chardev:mysensor`: Connects the next UART (`/dev/ttymxc1`) to this socket.

### ✅ Testing the UART Link

In your Linux system running inside QEMU:

```sh
echo "HELLO" > /dev/ttymxc1
```

Then, on the host or another terminal:

```bash
nc 127.0.0.1 4444
```

You should see `HELLO` printed in the netcat session.

### ⚠️ Reminder

QEMU assigns serial ports in order:

| QEMU Argument             | Linux Device     |
|--------------------------|------------------|
| `-serial stdio`          | `/dev/ttymxc0`   |
| `-serial chardev:XXX`    | `/dev/ttymxc1`   |
| ...                      | ...              |

If no backend is connected for a serial port declared in the Device Tree, and the kernel attempts to access it, a **kernel panic** or crash may occur.

---

You can also use other chardev types such as `file`, `pty`, or `pipe`, depending on how you want to simulate your sensor or logging.

Example with PTY:

```bash
-chardev pty,id=mypty -serial chardev:mypty
```

QEMU will print the pseudo-terminal path (e.g., `/dev/pts/5`), which you can use from the host.

## ✅ QEMU Options Summary

| Option | Required? | Description |
|--------|-----------|-------------|
| `-monitor none` | ✅ Yes | Prevents QEMU from using the terminal for interactive monitor. |
| `-serial stdio` | ✅ Yes | Connects the serial console (ttymxc0) to your terminal. |
| `-chardev ...` | ✅ If using sensors via socket or pipe | Additional backend for another UART (like ttymxc1). |
| `-serial chardev:...` | ✅ For associating UART1/2/3 to external sensors | Maps UARTs to specific character device backends. |

### Notes:
- **`-monitor none`** is essential to avoid terminal conflicts
- **`-serial stdio`** provides the main Linux console access
- **`-chardev`** creates the communication backend (socket, file, pty, etc.)
- **`-serial chardev:`** links the UART device to the character device backend

## ⚠️ Important: QEMU Option Order

### ✅ Recommended Order
```bash
qemu-system-arm \
  ... \
  -monitor none \
  -serial stdio \
  -serial chardev:mysensor \
  ...
```

### ❌ Problematic Order (Risk of Conflict)
```bash
qemu-system-arm \
  ... \
  -serial stdio \
  -serial chardev:mysensor \
  -monitor none
```

In this order, QEMU may have already initialized the monitor as stdin/stdout (by default), and when you add `-serial stdio` afterwards, it conflicts with the same channel.

### 🎯 Recommendation

Always place `-monitor none`:
- **Before** `-serial stdio`
- **Or** right after `-kernel`, `-dtb`, `-initrd`, etc.

This ensures that no other option takes the terminal as a backend prematurely, avoiding conflicts between the monitor and serial console.

### Why Order Matters
1. **QEMU processes options sequentially**
2. **Default monitor uses stdin/stdout**
3. **`-serial stdio` also needs stdin/stdout**
4. **`-monitor none` disables the default monitor first**
5. **This prevents terminal channel conflicts**

## 🔍 Identifying UART Devices and Addresses

### Check Available UART Devices
To identify which UART devices are available and their memory addresses:

```bash
~ # dmesg | grep ttymxc
[    5.481987] 2020000.serial: ttymxc0 at MMIO 0x2020000 ...
[    5.525575] 21e8000.serial: ttymxc1 at MMIO 0x21e8000 ...
```

## Mapping Device Tree UART Nodes to /dev/ttymxcN

| Device Tree Node | Physical Address | Linux Device |
|------------------|------------------|--------------|
| &uart1           | 0x2020000        | /dev/ttymxc0 |
| &uart2           | 0x21e8000        | /dev/ttymxc1 |
| &uart3           | 0x21ec000        | /dev/ttymxc2 |
| &uart4           | 0x21f0000        | /dev/ttymxc3 |
| &uart5           | 0x21f4000        | /dev/ttymxc4 |

### 🔧 Finding the Corresponding Device Tree Node

Look for `reg = <0x21e8000 ...>` in your `.dts` or `.dtsi` files.

**Found in `imx6qdl.dtsi`:**

```dts
uart2: serial@21e8000 {
    compatible = "fsl,imx6q-uart", "fsl,imx21-uart";
    reg = <0x021e8000 0x4000>;
    interrupts = <0 27 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&clks IMX6QDL_CLK_UART_IPG>,
             <&clks IMX6QDL_CLK_UART_SERIAL>;
    clock-names = "ipg", "per";
    dmas = <&sdma 27 4 0>, <&sdma 28 4 0>;
    dma-names = "rx", "tx";
    status = "disabled";
};
```

→ The name `uart2:` is an internal alias, but the important part is that the base address `0x21e8000` matches → therefore it corresponds to `/dev/ttymxc1`.

**Note:** This configuration is found in `imx6qdl.dtsi`, which is included by most i.MX6 device tree files.

### ✅ Device Tree Configuration

For `/dev/ttymxc1`, the node you should modify in `linux-imx-5.10/arch/arm/boot/dts/imx6qdl-sabrelite.dtsi` is:

```dts
&uart2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart2>; // or whatever you have
    status = "okay";
    dmas = <>; // ← IMPORTANT: Empty DMA to avoid kernel panic
};
```

### ⚠️ IMPORTANT: DMA Configuration

The `dmas = <>;` (empty DMA configuration) is crucial in QEMU environments to prevent kernel panics when accessing UARTs that don't have proper DMA emulation backing.

## 🔧 SDMA Configuration for QEMU

### SDMA Node in imx6qdl.dtsi

The SDMA (Smart DMA) controller is configured as follows:

```dts
sdma: sdma@20ec000 {
    compatible = "fsl,imx6q-sdma", "fsl,imx35-sdma";
    reg = <0x020ec000 0x4000>;
    interrupts = <0 2 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&clks IMX6QDL_CLK_IPG>,
             <&clks IMX6QDL_CLK_SDMA>;
    clock-names = "ipg", "ahb";
    #dma-cells = <3>;
    fsl,sdma-ram-script-name = "imx/sdma/sdma-imx6q.bin";
    status = "disabled";
};
```

### ⚠️ QEMU Workaround

**Add `status = "disabled"` to the SDMA node in `imx6qdl.dtsi`** to prevent SDMA-related kernel panics in QEMU environments.

This disables the SDMA controller entirely, which is why we need to use empty DMA configurations (`dmas = <>;`) in UART nodes when running in QEMU.

### ✅ Verify SDMA Status

To check if SDMA is properly disabled in the running system:

```bash
~ # cat /proc/device-tree/soc/bus@2000000/sdma@20ec000/status 
disabled~ # 
```

If the output shows "disabled", the SDMA controller is correctly disabled and won't cause kernel panics when accessing UARTs.


# Device Tree Source (DTS) Configurations

## Board Configuration Hierarchy

### imx6q-sabresd.dts
Board specific configurations inherits from:
- **`imx6q.dtsi`** → CPU, Clocks, Memory, Common Peripherals
- **`imx6qdl-sabresd.dtsi`** → Pin definitions UARTs, LCD, etc

## UART Configuration Examples

### Pin Control Configuration (`imx6qdl-sabrelite.dtsi`)
```dts
pinctrl_uart2: uart2grp {
    fsl,pins = <
        MX6QDL_PAD_EIM_D26__UART2_TX_DATA	0x1b0b1
        MX6QDL_PAD_EIM_D27__UART2_RX_DATA	0x1b0b1
    >;
};
```

### UART Device Configuration (`imx6q-sabrelite.dts`)
```dts
&uart2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart2>;
    status = "okay";
};
```

## Runtime Verification

### Check Available TTY Devices
```bash
dmesg | grep tty
```
Expected output:
```
ttymxc0 at ...
ttymxc1 at ...
```

### Test UART Communication
```bash
echo "HELLO" > /dev/ttymxc1
```

## Notes
- Device tree configuration enables hardware peripherals at boot time
- Pin control settings configure GPIO multiplexing for UART functions
- Multiple UART devices (ttymxc0, ttymxc1) available on i.MX6 platforms


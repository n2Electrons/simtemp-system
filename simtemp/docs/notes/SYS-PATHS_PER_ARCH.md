# Platform Driver Paths Comparison

## ARM Platform (QEMU ARM emulation)
```
/sys/bus/platform/drivers/nxp-simtemp/
/sys/devices/platform/simtemp/
```

## Docker x86_64 / Debian
```
/sys/bus/platform/drivers/nxp-simtemp/
/sys/devices/platform/nxp-simtemp.0/
/sys/devices/platform/nxp-simtemp.1.auto/
```

## Host x86_64 / Ubuntu
```
/sys/bus/platform/drivers/nxp-simtemp/
/sys/devices/platform/nxp-simtemp.0/
/sys/devices/platform/nxp-simtemp.1.auto/
```

## Notes

- **ARM Platform**: Uses simplified device naming (`simtemp`) in QEMU emulation
- **x86_64 Platforms**: Both Docker/Debian and Host/Ubuntu show identical paths with auto-generated device instances (`.0` and `.1.auto`)
- **Driver Path**: Consistent across all platforms (`/sys/bus/platform/drivers/nxp-simtemp/`)
- **Device Instances**: x86_64 platforms create multiple device instances automatically

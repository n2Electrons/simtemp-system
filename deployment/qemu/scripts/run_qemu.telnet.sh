#!/bin/sh

DOCKER_ENV="/.dockerenv"

if [ -e "$DOCKER_ENV" ]; then
  KERNEL_IMAGE="/workspace/deployment/qemu/linux-build-imx/arch/arm/boot/zImage"
  DTB_FILE="/workspace/deployment/qemu/imx6q-sabresd-with-simtemp.dtb"
  ROOTFS_IMAGE="/workspace/deployment/qemu/rootfs.cpio.gz"
else
  KERNEL_IMAGE="linux-build-imx/arch/arm/boot/zImage"
  #DTB_FILE="imx6q-sabresd-with-simtemp.dtb"
  #DTB_FILE="imx6q-sabrelite.dtb"
  DTB_FILE="imx6q-sabrelite-with-simtemp.dtb"
  ROOTFS_IMAGE="rootfs.cpio.gz"
fi

echo "Current working directory: $(pwd)"
echo "KERNEL_IMAGE env var: '$KERNEL_IMAGE'"
echo "DTB_FILE env var: '$DTB_FILE'"
echo "ROOTFS_IMAGE env var: '$ROOTFS_IMAGE'"

# Networking and ports
# Use a dedicated monitor port to avoid clashing with telnet port forwarding
MONITOR_PORT=45455
TELNET_PORT=2323   # host TCP port exposing the guest serial console via Telnet
SENSOR_PORT=4445   # existing sensor socket

INTERACTIVE=0

# Minimal arg parsing: --interactive or -i switches serial to stdio
case "${1-}" in
  -i|--interactive)
    INTERACTIVE=1
    shift
    ;;
  *)
    :
    ;;
esac

echo "Monitor (QEMU) port: $MONITOR_PORT"
if [ "$INTERACTIVE" -eq 1 ]; then
  echo "Serial console: stdio (this terminal)"
else
  echo "Serial console exposed on: telnet localhost:$TELNET_PORT"
fi


# Same setup for automation in host and in docker
# -monitor null to avoid conflicts
# -serial stdio without interactive monitor
# Let automation happen without manual intervention
# Same setup for automation in host and in docker
# -monitor telnet on a dedicated port
# -serial stdio without interactive monitor
# Add user networking with host port forwarding for telnetd

# Verify qemu available
if ! command -v qemu-system-arm >/dev/null 2>&1; then
  echo "ERROR: qemu-system-arm not found. Please install qemu-system-arm." >&2
  exit 1
fi

# No guest-network dependency for remote commands by default.
# If you need guest networking, wire it separately (e.g., -netdev/-device).
NET_ARGS=""

# Choose serial backend: telnet (default, automation) or stdio (interactive)
if [ "$INTERACTIVE" -eq 1 ]; then
  SERIAL_ARG="-serial stdio"
else
  SERIAL_ARG="-serial telnet:127.0.0.1:${TELNET_PORT},server,nowait"
fi

qemu-system-arm -M sabrelite \
  -cpu cortex-a9 \
  -m 1024 -nographic -no-reboot \
  -kernel "$KERNEL_IMAGE" \
  -dtb "$DTB_FILE" \
  -initrd "$ROOTFS_IMAGE" \
  -append "console=ttymxc0,115200 rdinit=/init" \
  -monitor telnet:127.0.0.1:${MONITOR_PORT},server,nowait \
  $SERIAL_ARG \
  -chardev socket,id=mysensor,server=on,host=127.0.0.1,port=${SENSOR_PORT},wait=off \
  -serial chardev:mysensor \
  ${NET_ARGS}

#  -monitor none \
#  -serial stdio \
# -serial telnet:127.0.0.1:2323,server,nowait \

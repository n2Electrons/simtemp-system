# Source this file:  source ./imx-env.sh
export ARCH="arm"
export CROSS_COMPILE="arm-linux-gnueabihf-"
export SYSROOT="/home/jorge/challenge-2509/simtemp-system/simtemp/scripts/sysroot-arm"
export KERNEL_SRC="/home/jorge/challenge-2509/simtemp-system/deployment/qemu/linux-imx-5.10"
# For pkg-config cross lookups (adjust if needed)
export PKG_CONFIG_SYSROOT_DIR="$SYSROOT"
export PKG_CONFIG_LIBDIR="$SYSROOT/usr/lib/pkgconfig:$SYSROOT/usr/lib/arm-linux-gnueabihf/pkgconfig:$SYSROOT/usr/share/pkgconfig"
export PKG_CONFIG_PATH=
# For kernel module builds (if --modules was used)
export KDIR="$KERNEL_SRC"

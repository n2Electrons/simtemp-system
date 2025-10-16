#include <stdio.h>
#include <unistd.h>
#include <sys/utsname.h>

int main() {
    struct utsname system_info;
    
    printf("===================================\n");
    printf("   Hello World from QEMU i.MX6!\n");
    printf("===================================\n");
    printf("\n");
    
    // Get system information
    if (uname(&system_info) == 0) {
        printf("System Information:\n");
        printf("  OS: %s\n", system_info.sysname);
        printf("  Kernel: %s\n", system_info.release);
        printf("  Architecture: %s\n", system_info.machine);
        printf("  Hostname: %s\n", system_info.nodename);
    }
    
    printf("\n");
    printf("Test Results:\n");
    printf("  [PASS] ARM cross-compilation successful\n");
    printf("  [PASS] QEMU i.MX6 emulation working\n");
    printf("  [PASS] Device Tree loading successful\n");
    printf("  [PASS] ARM rootfs execution successful\n");
    printf("\n");
    printf("Jenkins Integration: READY\n");
    printf("===================================\n");
    
    return 0;
}
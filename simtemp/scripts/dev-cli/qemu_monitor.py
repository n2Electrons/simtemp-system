#!/usr/bin/env python3
import time
import psutil
from datetime import datetime
import os
import sys

MONITOR_INTERVAL = 1.0  # seconds
QEMU_BIN = "qemu-system-arm"

# Store known qemu pids
known_pids = set()

print(f"[QEMU-MONITOR] Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

while True:
    # Find all qemu-system-arm processes
    qemu_procs = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
        cmdline = p.info.get('cmdline', [])
        if cmdline and QEMU_BIN in ' '.join(cmdline):
            qemu_procs.append(p)
    
    current_pids = set(p.info['pid'] for p in qemu_procs)
    new_pids = current_pids - known_pids
    for pid in new_pids:
        proc = next((p for p in qemu_procs if p.info['pid'] == pid), None)
        if proc:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            cmdline = proc.info.get('cmdline', [])
            cmdline_str = ' '.join(cmdline) if cmdline else '(no cmdline)'
            ppid = proc.info.get('ppid')
            parent_cmd = ''
            try:
                parent = psutil.Process(ppid)
                parent_cmd = ' '.join(parent.cmdline())
            except Exception:
                parent_cmd = '(parent info unavailable)'
            print(f"[QEMU-MONITOR] [{ts}] NEW QEMU PROCESS: PID={pid} CMD='{cmdline_str}'")
            print(f"[QEMU-MONITOR] [{ts}]   Created by PID={ppid} CMD='{parent_cmd}'")
    known_pids = current_pids
    time.sleep(MONITOR_INTERVAL)

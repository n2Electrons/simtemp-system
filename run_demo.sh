#!/bin/bash

cd simtemp/user/gui/                        # Python GUI App. Connects to CLI via socket 4446
xterm -e ./run_gui.sh &
cd ../../../deployment/qemu/
xterm -e ./scripts/run-qemu-ssh.sh &    # QEMU VM with SimTemp firmware. CLI connects via Telnet 4445   
cd ../..        
xterm -e python3 simtemp-remote-cli.py           # CLI connects to the QEMU VM via via Telnet 4445

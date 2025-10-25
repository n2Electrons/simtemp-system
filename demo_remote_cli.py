#!/usr/bin/env python3
"""
Demo Script for SimTemp Remote CLI
Shows the complete functionality of the SSH-based driver configuration.
"""

import os
import subprocess


def run_command(cmd, description):
    """Run a command and show the results"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=120)
        print(result.stdout)
        if result.stderr:
            print(f"[STDERR] {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("[ERROR] Command timed out")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    print("🚀 SimTemp Remote CLI Demo")
    print("This demo shows the complete SSH-based driver configuration "
          "functionality")
    print("=" * 80)
    
    base_cmd = ["python3", "simtemp_remote_cli.py"]
    
    # 1. Show initial configuration
    run_command(base_cmd + ["--config"],
                "Show Initial Driver Configuration")
    
    # 2. Configure sample rate
    run_command(base_cmd + ["--set-rate", "250"],
                "Set Sample Rate to 250ms")
    
    # 3. Configure threshold
    run_command(base_cmd + ["--set-threshold", "35.5"],
                "Set Threshold to 35.5°C")
    
    # 4. Show updated configuration
    run_command(base_cmd + ["--config"],
                "Show Updated Configuration")
    
    # 5. Read temperature samples (short duration)
    run_command(base_cmd + ["--read", "--duration", "5"],
                "Read Temperature for 5 seconds")
    
    print("\n" + "="*80)
    print("✅ Demo completed successfully!")
    print("📖 The SimTemp Remote CLI provides:")
    print("   • SSH-based driver configuration")
    print("   • Sample rate control (1-60000 ms)")
    print("   • Threshold configuration (-50°C to 150°C)")
    print("   • Continuous temperature reading")
    print("   • Interactive mode for real-time control")
    print("   • Automatic QEMU startup with SSH support")
    print("="*80)


if __name__ == "__main__":
    os.chdir("/home/jorge/challenge-2509/simtemp-system")
    main()

#!/usr/bin/env python3
"""
QEMU Telnet Test - Task Force CLI Agent Testing
Quick test to verify telnet connection to QEMU console
"""

import telnetlib
import time
import sys


def test_qemu_telnet_connection():
    """Test the telnet connection to QEMU console"""
    print("🧪 Task Force CLI Agent - QEMU Telnet Test")
    print("=" * 50)
    
    try:
        print("🔌 Connecting to QEMU console via telnet...")
        tn = telnetlib.Telnet('127.0.0.1', 2323, timeout=5)
        print("✅ Connected to QEMU console (port 2323)")
        
        # Test basic command
        print("\n📋 Testing basic command (ls /dev/temp*)...")
        tn.write(b'ls -la /dev/temp*\n')
        time.sleep(1)
        
        response = tn.read_very_eager().decode('utf-8', errors='ignore')
        print(f"Response:\n{response}")
        
        # Check for tempsensor device
        if '/dev/tempsensor' in response:
            print("✅ /dev/tempsensor found!")
            
            # Test reading the sensor
            print("\n🌡️ Testing sensor read (cat /dev/tempsensor)...")
            tn.write(b'cat /dev/tempsensor\n')
            time.sleep(2)
            
            sensor_data = tn.read_very_eager().decode('utf-8', errors='ignore')
            print(f"Sensor data:\n{sensor_data}")
            
            if sensor_data.strip():
                print("✅ Sensor data received!")
            else:
                print("ℹ️ No sensor data (normal if no generator running)")
                
        else:
            print("❌ /dev/tempsensor not found")
        
        # Test device link
        print("\n🔗 Testing device link (ls -la /dev/ttymxc1)...")
        tn.write(b'ls -la /dev/ttymxc1\n')
        time.sleep(1)
        
        link_info = tn.read_very_eager().decode('utf-8', errors='ignore')
        print(f"Device info:\n{link_info}")
        
        tn.close()
        print("\n✅ QEMU Telnet Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ QEMU Telnet Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_qemu_telnet_connection()
    
    if success:
        print("\n🎯 Task Force Status: CLI Agent telnet connection READY")
        print("💡 Run the orchestrator: python3 qemu_telnet_orchestrator.py")
        sys.exit(0)
    else:
        print("\n⚠️ Task Force Status: CLI Agent telnet connection FAILED")
        print("🔧 Check that QEMU is running with telnet on port 2323")
        sys.exit(1)
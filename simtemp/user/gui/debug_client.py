#!/usr/bin/env python3
"""
Debug version of SimTemp GUI client to see exactly what the bridge is sending
"""

import socket
import time

def debug_bridge_communication():
    """Connect to bridge and show raw responses"""
    print("🔍 Debug: Connecting to SimTemp Protocol Bridge on port 4446...")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 4446))
        print("✅ Connected!")
        
        # Get welcome message
        welcome = s.recv(1024)
        print(f"📨 Welcome message: {repr(welcome)}")
        
        # Test GET_TEMP
        print("\n🌡️ Testing GET_TEMP command...")
        s.send(b'GET_TEMP\n')
        temp_response = s.recv(1024)
        print(f"📨 GET_TEMP response: {repr(temp_response)}")
        
        # Test STATUS  
        print("\n📊 Testing STATUS command...")
        s.send(b'STATUS\n')
        status_response = s.recv(1024)
        print(f"📨 STATUS response: {repr(status_response)}")
        
        s.close()
        print("\n✅ Debug session completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_bridge_communication()
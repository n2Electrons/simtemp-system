#!/usr/bin/env python3
"""
Simple GUI Test for SimTemp Protocol Bridge
Testing the GUI Protocol Integration without external dependencies
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import sys
import os

# Add current directory to path for importing the client
sys.path.append(os.path.dirname(__file__))
from external_simtemp_client import ExternalSimTempClient


class SimpleGUITest:
    """Simple GUI to test SimTemp Protocol Bridge integration."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SimTemp Protocol Bridge - GUI Test")
        self.root.geometry("600x400")
        
        # Client
        self.client = None
        self.monitoring = False
        self.monitor_thread = None
        
        # GUI Variables
        self.temperature_var = tk.StringVar(value="--.-°C")
        self.status_var = tk.StringVar(value="Disconnected")
        self.bridge_info_var = tk.StringVar(value="No bridge info")
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the GUI components."""
        # Title
        title_label = tk.Label(
            self.root, 
            text="SimTemp Protocol Bridge - GUI Integration Test",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # Connection frame
        conn_frame = tk.LabelFrame(self.root, text="Connection", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=20, pady=5)
        
        # Host and port
        tk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky="w")
        self.host_entry = tk.Entry(conn_frame, width=15)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=0, column=1, padx=5)
        
        tk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky="w")
        self.port_entry = tk.Entry(conn_frame, width=8)
        self.port_entry.insert(0, "4446")
        self.port_entry.grid(row=0, column=3, padx=5)
        
        # Connect button
        self.connect_btn = tk.Button(
            conn_frame, 
            text="Connect", 
            command=self.toggle_connection,
            bg="lightgreen"
        )
        self.connect_btn.grid(row=0, column=4, padx=10)
        
        # Status
        status_frame = tk.LabelFrame(self.root, text="Status", padx=10, pady=10)
        status_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(status_frame, text="Connection:").grid(row=0, column=0, sticky="w")
        tk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w")
        
        # Temperature display
        temp_frame = tk.LabelFrame(self.root, text="Temperature", padx=10, pady=10)
        temp_frame.pack(fill="x", padx=20, pady=5)
        
        temp_display = tk.Label(
            temp_frame,
            textvariable=self.temperature_var,
            font=("Arial", 24, "bold"),
            fg="blue"
        )
        temp_display.pack()
        
        # Bridge info
        info_frame = tk.LabelFrame(self.root, text="Bridge Information", padx=10, pady=10)
        info_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.info_text = tk.Text(info_frame, height=8, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20, pady=5)
        
        self.monitor_btn = tk.Button(
            btn_frame,
            text="Start Monitoring",
            command=self.toggle_monitoring,
            state="disabled"
        )
        self.monitor_btn.pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Get Temperature",
            command=self.get_single_temperature,
            state="disabled"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Get Status",
            command=self.get_single_status,
            state="disabled"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Get Bridge Info",
            command=self.get_bridge_info,
            state="disabled"
        ).pack(side="left", padx=5)
        
        # Store button references
        self.action_buttons = [
            self.monitor_btn,
            btn_frame.winfo_children()[1],
            btn_frame.winfo_children()[2], 
            btn_frame.winfo_children()[3]
        ]
    
    def toggle_connection(self):
        """Toggle connection to bridge."""
        if self.client and self.client.connected:
            # Disconnect
            if self.monitoring:
                self.toggle_monitoring()
            
            self.client.disconnect()
            self.client = None
            
            self.status_var.set("Disconnected")
            self.connect_btn.config(text="Connect", bg="lightgreen")
            
            for btn in self.action_buttons:
                btn.config(state="disabled")
                
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, "Disconnected from bridge\\n")
            
        else:
            # Connect
            host = self.host_entry.get()
            port = int(self.port_entry.get())
            
            self.client = ExternalSimTempClient(host, port)
            
            if self.client.connect():
                self.status_var.set(f"Connected to {host}:{port}")
                self.connect_btn.config(text="Disconnect", bg="lightcoral")
                
                for btn in self.action_buttons:
                    btn.config(state="normal")
                
                # Show bridge info on connect
                self.get_bridge_info()
                
            else:
                messagebox.showerror("Connection Error", f"Failed to connect to {host}:{port}")
                self.client = None
    
    def get_single_temperature(self):
        """Get single temperature reading."""
        if self.client:
            temp = self.client.get_temperature()
            if temp is not None:
                self.temperature_var.set(f"{temp:.1f}°C")
                self.info_text.insert(tk.END, f"Temperature: {temp:.1f}°C\\n")
                self.info_text.see(tk.END)
            else:
                self.info_text.insert(tk.END, "Failed to get temperature\\n")
                self.info_text.see(tk.END)
    
    def get_single_status(self):
        """Get single status reading."""
        if self.client:
            status = self.client.get_status()
            if status:
                self.info_text.insert(tk.END, f"Status: {status}\\n")
                self.info_text.see(tk.END)
                
                # Update temperature display if available
                if 'temperature' in status:
                    self.temperature_var.set(f"{status['temperature']:.1f}°C")
            else:
                self.info_text.insert(tk.END, "Failed to get status\\n")
                self.info_text.see(tk.END)
    
    def get_bridge_info(self):
        """Get bridge information."""
        if self.client:
            info = self.client.get_bridge_info()
            if info:
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, "=== Bridge Information ===\\n")
                for key, value in info.items():
                    self.info_text.insert(tk.END, f"{key}: {value}\\n")
                self.info_text.insert(tk.END, "\\n")
                self.info_text.see(tk.END)
            else:
                self.info_text.insert(tk.END, "Failed to get bridge info\\n")
                self.info_text.see(tk.END)
    
    def toggle_monitoring(self):
        """Toggle continuous monitoring."""
        if not self.monitoring:
            # Start monitoring
            self.monitoring = True
            self.monitor_btn.config(text="Stop Monitoring")
            
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            self.info_text.insert(tk.END, "Started continuous monitoring\\n")
            self.info_text.see(tk.END)
        else:
            # Stop monitoring
            self.monitoring = False
            self.monitor_btn.config(text="Start Monitoring")
            
            self.info_text.insert(tk.END, "Stopped continuous monitoring\\n")
            self.info_text.see(tk.END)
    
    def monitor_loop(self):
        """Continuous monitoring loop."""
        while self.monitoring and self.client and self.client.connected:
            try:
                temp = self.client.get_temperature()
                if temp is not None:
                    # Update GUI in main thread
                    self.root.after(0, self.update_temperature_display, temp)
                
                time.sleep(2)  # 2 second interval
                
            except Exception as e:
                self.root.after(0, self.monitoring_error, str(e))
                break
    
    def update_temperature_display(self, temperature):
        """Update temperature display (called from main thread)."""
        self.temperature_var.set(f"{temperature:.1f}°C")
        
        # Color based on threshold (example: 45°C)
        if temperature >= 45.0:
            self.root.winfo_children()[2].winfo_children()[0].config(fg="red")
        else:
            self.root.winfo_children()[2].winfo_children()[0].config(fg="blue")
    
    def monitoring_error(self, error_msg):
        """Handle monitoring error (called from main thread)."""
        self.monitoring = False
        self.monitor_btn.config(text="Start Monitoring")
        self.info_text.insert(tk.END, f"Monitoring error: {error_msg}\\n")
        self.info_text.see(tk.END)
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    print("=" * 60)
    print("SimTemp Protocol Bridge - GUI Integration Test")
    print("=" * 60)
    print()
    print("This GUI tests the integration with SimTemp Protocol Bridge")
    print("Default connection: 127.0.0.1:4446")
    print()
    
    app = SimpleGUITest()
    app.run()


if __name__ == "__main__":
    main()
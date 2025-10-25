#!/usr/bin/env python3
"""
Configuration Control Panel
Copyright (c) 2025 Jorge Rodriguez Moreno

Control panel with sliders for threshold and sample rate configuration.
"""

import customtkinter as ctk
import sys
import os

# Add CLI path for importing configuration client
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cli'))

try:
    from simtemp_config_client import SimTempConfigClient
except ImportError:
    print("Warning: SimTempConfigClient not available")
    SimTempConfigClient = None


class ConfigurationPanel(ctk.CTkFrame):
    """
    Configuration control panel with sliders for threshold and sample rates.
    """
    
    def __init__(self, master, width=300, height=400, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        
        self.width = width
        self.height = height
        
        # Configuration client
        self.config_client = None
        self.host = "127.0.0.1"
        self.port = 4446  # SimTemp Protocol Bridge port
        
        # Current values
        self.current_threshold = 45.0
        self.current_sample_rate = 100  # ms
        
        # Predefined sample rates (in milliseconds)
        self.sample_rates = [50, 100, 250, 500, 1000, 2000, 5000]
        self.sample_rate_labels = ["50ms", "100ms", "250ms", "500ms", 
                                  "1s", "2s", "5s"]
        
        # Callbacks
        self.threshold_callback = None
        self.sample_rate_callback = None
        self.connection_callback = None
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the configuration panel UI."""
        # Title
        title_label = ctk.CTkLabel(self, text="Configuration Panel", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=(10, 20))
        
        # Connection section
        self.setup_connection_section()
        
        # Threshold section
        self.setup_threshold_section()
        
        # Sample rate section
        self.setup_sample_rate_section()
        
        # Status section
        self.setup_status_section()
    
    def setup_connection_section(self):
        """Setup connection controls."""
        conn_frame = ctk.CTkFrame(self)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        # Connection title
        conn_label = ctk.CTkLabel(conn_frame, text="Connection", 
                                 font=ctk.CTkFont(size=14, weight="bold"))
        conn_label.pack(pady=(10, 5))
        
        # Host and port entries
        host_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
        host_frame.pack(fill="x", padx=10, pady=5)
        
        host_label = ctk.CTkLabel(host_frame, text="Host:")
        host_label.pack(side="left")
        
        self.host_entry = ctk.CTkEntry(host_frame, width=120)
        self.host_entry.pack(side="right", padx=(5, 0))
        self.host_entry.insert(0, self.host)
        
        port_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=10, pady=5)
        
        port_label = ctk.CTkLabel(port_frame, text="Port:")
        port_label.pack(side="left")
        
        self.port_entry = ctk.CTkEntry(port_frame, width=120)
        self.port_entry.pack(side="right", padx=(5, 0))
        self.port_entry.insert(0, str(self.port))
        
        # Connect button
        self.connect_button = ctk.CTkButton(conn_frame, text="Connect",
                                          command=self.connect_to_sensor)
        self.connect_button.pack(pady=(10, 5))
        
        # Disconnect button (red text, white background)
        self.disconnect_button = ctk.CTkButton(conn_frame, text="Disconnect",
                                             command=self.disconnect_from_sensor,
                                             text_color="red",
                                             fg_color="white",
                                             hover_color="#f0f0f0",
                                             state="disabled")
        self.disconnect_button.pack(pady=(0, 10))
        
        # Connection status with visual indicator (moved to top right)
        status_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
        status_frame.pack(pady=(0, 10))
        
        # Status indicator circle
        self.status_circle = ctk.CTkLabel(status_frame, text="●",
                                         text_color="red",
                                         font=ctk.CTkFont(size=16))
        self.status_circle.pack(side="left", padx=(0, 5))
        
        # Connection status text
        self.connection_status = ctk.CTkLabel(status_frame,
                                             text="Disconnected",
                                             text_color="white")
        self.connection_status.pack(side="left")
    
    def setup_threshold_section(self):
        """Setup threshold configuration controls."""
        threshold_frame = ctk.CTkFrame(self)
        threshold_frame.pack(fill="x", padx=10, pady=5)
        
        # Threshold title
        threshold_label = ctk.CTkLabel(threshold_frame,
                                     text="Temperature Threshold",
                                     font=ctk.CTkFont(size=14, weight="bold"))
        threshold_label.pack(pady=(10, 5))
        
        # Threshold value display (two lines)
        self.threshold_title_label = ctk.CTkLabel(threshold_frame,
                                                text="Current Threshold",
                                                font=ctk.CTkFont(size=12))
        self.threshold_title_label.pack()
        
        self.threshold_value_label = ctk.CTkLabel(threshold_frame,
                                                text=f"{self.current_threshold:.1f}°C",
                                                font=ctk.CTkFont(size=18,
                                                               weight="bold"))
        self.threshold_value_label.pack(pady=(0, 5))
        
        # Threshold slider
        self.threshold_slider = ctk.CTkSlider(threshold_frame, from_=0, to=100,
                                            number_of_steps=200,
                                            command=self.on_threshold_change)
        self.threshold_slider.pack(fill="x", padx=10, pady=5)
        self.threshold_slider.set(self.current_threshold)
        
        # Threshold range labels
        range_frame = ctk.CTkFrame(threshold_frame, fg_color="transparent")
        range_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        min_label = ctk.CTkLabel(range_frame, text="0°C")
        min_label.pack(side="left")
        
        max_label = ctk.CTkLabel(range_frame, text="100°C")
        max_label.pack(side="right")
        
        # Apply threshold button
        self.apply_threshold_btn = ctk.CTkButton(threshold_frame, 
                                               text="Apply Threshold",
                                               command=self.apply_threshold)
        self.apply_threshold_btn.pack(pady=(0, 10))
        self.apply_threshold_btn.configure(state="disabled")
    
    def setup_sample_rate_section(self):
        """Setup sample rate configuration controls."""
        sample_frame = ctk.CTkFrame(self)
        sample_frame.pack(fill="x", padx=10, pady=5)
        
        # Sample rate title
        sample_label = ctk.CTkLabel(sample_frame, text="Sample Rate", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        sample_label.pack(pady=(10, 5))
        
        # Sample rate value display
        self.sample_rate_value_label = ctk.CTkLabel(sample_frame, 
                                                  text=f"{self.current_sample_rate}ms",
                                                  font=ctk.CTkFont(size=18))
        self.sample_rate_value_label.pack(pady=5)
        
        # Sample rate slider (stepped)
        self.sample_rate_slider = ctk.CTkSlider(sample_frame, from_=0, 
                                              to=len(self.sample_rates)-1,
                                              number_of_steps=len(self.sample_rates)-1,
                                              command=self.on_sample_rate_change)
        self.sample_rate_slider.pack(fill="x", padx=10, pady=5)
        
        # Set initial position
        initial_index = self.sample_rates.index(self.current_sample_rate)
        self.sample_rate_slider.set(initial_index)
        
        # Sample rate labels
        labels_frame = ctk.CTkFrame(sample_frame, fg_color="transparent")
        labels_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        fast_label = ctk.CTkLabel(labels_frame, text="Fast")
        fast_label.pack(side="left")
        
        slow_label = ctk.CTkLabel(labels_frame, text="Slow")
        slow_label.pack(side="right")
        
        # Apply sample rate button
        self.apply_sample_rate_btn = ctk.CTkButton(sample_frame, 
                                                 text="Apply Sample Rate",
                                                 command=self.apply_sample_rate)
        self.apply_sample_rate_btn.pack(pady=(0, 10))
        self.apply_sample_rate_btn.configure(state="disabled")
    
    def setup_status_section(self):
        """Setup status display section."""
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status title
        status_label = ctk.CTkLabel(status_frame, text="Status", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        status_label.pack(pady=(10, 5))
        
        # Status text
        self.status_text = ctk.CTkTextbox(status_frame, height=80)
        self.status_text.pack(fill="x", padx=10, pady=(0, 10))
        self.status_text.insert("1.0", "Ready to connect...")
    
    def on_threshold_change(self, value):
        """Handle threshold slider change."""
        self.current_threshold = value
        self.threshold_value_label.configure(text=f"{value:.1f}°C")
        
        # Enable apply button
        self.apply_threshold_btn.configure(state="normal")
        
        # Call callback if set
        if self.threshold_callback:
            self.threshold_callback(value)
    
    def on_sample_rate_change(self, value):
        """Handle sample rate slider change."""
        index = int(round(value))
        if 0 <= index < len(self.sample_rates):
            self.current_sample_rate = self.sample_rates[index]
            label = self.sample_rate_labels[index]
            self.sample_rate_value_label.configure(text=label)
            
            # Enable apply button
            self.apply_sample_rate_btn.configure(state="normal")
            
            # Call callback if set
            if self.sample_rate_callback:
                self.sample_rate_callback(self.current_sample_rate)
    
    def connect_to_sensor(self):
        """Connect to SimTemp sensor."""
        # Connect
        self.host = self.host_entry.get()
        self.port = int(self.port_entry.get())
        
        if SimTempConfigClient:
            self.config_client = SimTempConfigClient(self.host, self.port)
            
            if self.config_client.connect():
                self.connection_status.configure(text="Connected")
                self.status_circle.configure(text_color="green")
                self.connect_button.configure(state="disabled")
                self.disconnect_button.configure(state="normal")
                self.apply_threshold_btn.configure(state="normal")
                self.apply_sample_rate_btn.configure(state="normal")
                self.add_status_message("Connected to SimTemp sensor")
                
                # Get current configuration
                self.get_current_config()
                
                if self.connection_callback:
                    self.connection_callback(True)
            else:
                self.connection_status.configure(text="Connection Failed")
                self.status_circle.configure(text_color="red")
                self.config_client = None
                self.add_status_message("Failed to connect to sensor")
        else:
            self.add_status_message("SimTempConfigClient not available")
    
    def disconnect_from_sensor(self):
        """Disconnect from SimTemp sensor."""
        if self.config_client:
            self.config_client.disconnect()
            self.config_client = None
            
        self.connection_status.configure(text="Disconnected")
        self.status_circle.configure(text_color="red")
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.apply_threshold_btn.configure(state="disabled")
        self.apply_sample_rate_btn.configure(state="disabled")
        self.add_status_message("Disconnected from sensor")
        
        if self.connection_callback:
            self.connection_callback(False)
    
    def apply_threshold(self):
        """Apply threshold configuration to sensor."""
        if self.config_client:
            threshold_mC = int(self.current_threshold * 1000)
            success = self.config_client.set_threshold(threshold_mC)
            
            if success:
                self.add_status_message(f"Threshold set to {self.current_threshold:.1f}°C")
                self.apply_threshold_btn.configure(state="disabled")
            else:
                self.add_status_message("Failed to set threshold")
    
    def apply_sample_rate(self):
        """Apply sample rate configuration to sensor."""
        if self.config_client:
            success = self.config_client.set_sampling_period(self.current_sample_rate)
            
            if success:
                self.add_status_message(f"Sample rate set to {self.current_sample_rate}ms")
                self.apply_sample_rate_btn.configure(state="disabled")
            else:
                self.add_status_message("Failed to set sample rate")
    
    def get_current_config(self):
        """Get current configuration from sensor."""
        if self.config_client:
            config = self.config_client.get_status()
            if config:
                self.add_status_message("Current sensor configuration:")
                self.add_status_message(f"  Temperature: {config.get('temperature', 'N/A')}")
                self.add_status_message(f"  Sampling: {config.get('sampling_ms', 'N/A')}ms")
                self.add_status_message(f"  Threshold: {config.get('threshold_celsius', 'N/A')}°C")
    
    def add_status_message(self, message):
        """Add message to status display."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert("end", f"[{timestamp}] {message}\\n")
        self.status_text.see("end")
    
    def set_threshold_callback(self, callback):
        """Set callback for threshold changes."""
        self.threshold_callback = callback
    
    def set_sample_rate_callback(self, callback):
        """Set callback for sample rate changes."""
        self.sample_rate_callback = callback
    
    def set_connection_callback(self, callback):
        """Set callback for connection state changes."""
        self.connection_callback = callback


def test_configuration_panel():
    """Test the configuration panel widget."""
    root = ctk.CTk()
    root.title("Configuration Panel Test")
    root.geometry("400x700")
    
    ctk.set_appearance_mode("dark")
    
    # Create configuration panel
    config_panel = ConfigurationPanel(root, width=350, height=650)
    config_panel.pack(padx=20, pady=20, fill="both", expand=True)
    
    # Set up callbacks
    def on_threshold_change(value):
        print(f"Threshold changed to: {value:.1f}°C")
    
    def on_sample_rate_change(value):
        print(f"Sample rate changed to: {value}ms")
    
    def on_connection_change(connected):
        print(f"Connection state: {'Connected' if connected else 'Disconnected'}")
    
    config_panel.set_threshold_callback(on_threshold_change)
    config_panel.set_sample_rate_callback(on_sample_rate_change)
    config_panel.set_connection_callback(on_connection_change)
    
    root.mainloop()


if __name__ == "__main__":
    test_configuration_panel()
#!/usr/bin/env python3
"""
SimTemp External GUI Application
Copyright (c) 2025 Jorge Rodriguez Moreno

Complete external GUI application for SimTemp sensor monitoring with:
- Temperature dial with threshold visualization
- 7-segment digital display
- Real-time temperature plotting
- Configuration controls for threshold and sample rates
- TCP connection to SimTemp sensor via QEMU
- Real-time data reception from Octave

Usage:
    source simtemp_gui_env/bin/activate
    python3 main.py
"""

import customtkinter as ctk
import threading
import time
import sys
import os
import logging
import socket
import json
from datetime import datetime

# Add CLI path for importing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cli'))

# Configure matplotlib to be less verbose
import matplotlib
matplotlib.set_loglevel('WARNING')

# Import our custom widgets
from temperature_dial import TemperatureDial
from seven_segment_display import SevenSegmentDisplay
from realtime_plot import RealTimePlot
from configuration_panel import ConfigurationPanel
from external_simtemp_client import ExternalSimTempClient

# Configure logging - Only show important messages
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLIDataServer:
    """TCP Server to receive temperature data from CLI"""
    
    def __init__(self, port=4446, data_callback=None, connection_callback=None):
        self.port = port
        self.data_callback = data_callback
        self.connection_callback = connection_callback
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.server_thread = None
        
    def start(self):
        """Start the TCP server"""
        if self.running:
            return
            
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
    def _run_server(self):
        """Run the TCP server loop"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("127.0.0.1", self.port))
            self.server_socket.listen(1)
            self.running = True
            
            print(f"GUI Data Server listening on port {self.port}")
            
            while self.running:
                try:
                    self.client_socket, addr = self.server_socket.accept()
                    print(f"✓ CLI client connected from {addr}")
                    
                    # Notify about CLI connection
                    if self.connection_callback:
                        self.connection_callback(True, addr)
                    
                    while self.running:
                        try:
                            data = self.client_socket.recv(1024).decode('utf-8').strip()
                            if data:
                                # Handle multiple JSON messages separated by newlines
                                for line in data.split('\n'):
                                    line = line.strip()
                                    if line:
                                        # Check if it's a JSON temperature message
                                        if line.startswith('{') and line.endswith('}'):
                                            try:
                                                temp_data = json.loads(line)
                                                if self.data_callback:
                                                    self.data_callback(temp_data)
                                            except json.JSONDecodeError:
                                                pass  # Ignore invalid JSON
                            else:
                                print("✗ CLI client disconnected")
                                # Notify about CLI disconnection
                                if self.connection_callback:
                                    self.connection_callback(False, None)
                                break
                        except socket.error:
                            print("✗ CLI connection lost")
                            # Notify about CLI disconnection
                            if self.connection_callback:
                                self.connection_callback(False, None)
                            break
                            
                except socket.error as e:
                    if self.running:
                        print(f"✗ CLI server socket error: {e}")
                        
        except Exception as e:
            print(f"✗ CLI server error: {e}")
        finally:
            print("✗ GUI Data Server stopped")
            self.stop()
            
    def stop(self):
        """Stop the TCP server"""
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


class SimTempExternalGUI:
    """
    Main GUI application for external SimTemp sensor monitoring.
    
    This application provides a comprehensive interface for monitoring
    and configuring a SimTemp sensor running on an ARM target system
    connected via QEMU.
    """
    
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("SimTemp External Monitor - Challenge 2025")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Data client
        self.data_client = None
        self.monitoring_active = False
        self.monitoring_thread = None

        # GUI Data Server for receiving data from CLI
        self.cli_server = CLIDataServer(
            port=4446,
            data_callback=self.on_cli_data_received,
            connection_callback=self.on_cli_connection_change
        )

        # Current sensor data
        self.current_temperature = 25.0
        self.current_threshold = 45.0
        self.alarm_active = False
        
        # GUI update rate limiting to prevent grab conflicts
        self.last_gui_update = 0
        self.gui_update_interval = 0.1  # Minimum 100ms between GUI updates

        # GUI components
        self.dial = None
        self.display = None
        self.plot = None
        self.config_panel = None
        self.status_bar = None

        # Setup GUI (this will trigger matplotlib initialization)
        self.setup_gui()

        # Setup callbacks and start services
        self.setup_callbacks()

        # Start GUI data server
        self.cli_server.start()

        # Bind cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_gui(self):
        """Setup the complete GUI layout."""
        # Create main container
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title bar
        self.setup_title_bar(main_container)
        
        # Main content area
        content_frame = ctk.CTkFrame(main_container)
        content_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Left panel (instruments)
        left_panel = ctk.CTkFrame(content_frame)
        left_panel.pack(side="left", fill="y", padx=(0, 5))
        
        # Center panel (plot)
        center_panel = ctk.CTkFrame(content_frame)
        center_panel.pack(side="left", fill="both", expand=True, padx=5)
        
        # Right panel (configuration)
        right_panel = ctk.CTkFrame(content_frame)
        right_panel.pack(side="right", fill="y", padx=(5, 0))
        
        # Setup panels
        self.setup_left_panel(left_panel)
        self.setup_center_panel(center_panel)
        self.setup_right_panel(right_panel)
        
        # Status bar
        self.setup_status_bar(main_container)
    
    def setup_title_bar(self, parent):
        """Setup application title bar."""
        title_frame = ctk.CTkFrame(parent)
        title_frame.pack(fill="x", pady=(0, 10))
        
        # Application title
        title_label = ctk.CTkLabel(
            title_frame,
            text="SimTemp External Monitor",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # Connection indicator (top right corner)
        connection_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        connection_frame.pack(side="right", padx=20, pady=15)
        
        self.connection_indicator = ctk.CTkLabel(
            connection_frame,
            text="⏳ Waiting for CLI connection",
            text_color="yellow",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.connection_indicator.pack(side="right")
        
        # Red alarm lamp
        self.alarm_lamp = ctk.CTkLabel(
            title_frame,
            text="🔴",
            font=ctk.CTkFont(size=20)
        )
        self.alarm_lamp.pack(side="right", padx=(0, 20), pady=15)
        self.alarm_lamp.pack_forget()  # Hidden initially
    
    def setup_left_panel(self, parent):
        """Setup left panel with temperature instruments."""
        # Panel title
        instruments_label = ctk.CTkLabel(
            parent,
            text="Temperature Instruments",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        instruments_label.pack(pady=(10, 20))
        
        # Temperature dial
        self.dial = TemperatureDial(parent, width=280, height=280)
        self.dial.pack(padx=10, pady=10)
        
        # 7-segment display
        self.display = SevenSegmentDisplay(parent, digits=5, width=280, height=80)
        self.display.pack(padx=10, pady=10)
        self.display.set_value(self.current_temperature)
        
        # Temperature statistics
        stats_frame = ctk.CTkFrame(parent)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        stats_label = ctk.CTkLabel(
            stats_frame,
            text="Statistics",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        stats_label.pack(pady=(10, 5))
        
        self.stats_text = ctk.CTkTextbox(stats_frame, height=100)
        self.stats_text.pack(fill="x", padx=10, pady=(0, 10))
        self.update_statistics()
    
    def setup_center_panel(self, parent):
        """Setup center panel with real-time plot."""
        # Panel title
        plot_label = ctk.CTkLabel(
            parent,
            text="Real-time Temperature Plot",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        plot_label.pack(pady=(10, 10))
        
        # Real-time plot
        self.plot = RealTimePlot(parent, width=600, height=450)
        self.plot.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Plot controls
        plot_controls = ctk.CTkFrame(parent)
        plot_controls.pack(fill="x", padx=10, pady=(0, 10))
        
        # Start/Stop monitoring
        self.monitoring_button = ctk.CTkButton(
            plot_controls,
            text="Start Monitoring",
            command=self.toggle_monitoring
        )
        self.monitoring_button.pack(side="left", padx=5, pady=5)
        
        # Clear plot
        clear_button = ctk.CTkButton(
            plot_controls,
            text="Clear Plot",
            command=self.clear_plot_data
        )
        clear_button.pack(side="left", padx=5, pady=5)
        
        # Export data
        export_button = ctk.CTkButton(
            plot_controls,
            text="Export Data",
            command=self.export_plot_data
        )
        export_button.pack(side="left", padx=5, pady=5)
        
        # Time window selector
        time_label = ctk.CTkLabel(plot_controls, text="Time Window:")
        time_label.pack(side="right", padx=(20, 5), pady=5)
        
        self.time_window_var = ctk.StringVar(value="5 min")
        time_window_menu = ctk.CTkOptionMenu(
            plot_controls,
            variable=self.time_window_var,
            values=["1 min", "5 min", "10 min", "30 min"],
            command=self.change_time_window
        )
        time_window_menu.pack(side="right", padx=5, pady=5)
    
    def setup_right_panel(self, parent):
        """Setup right panel with configuration controls."""
        # Configuration panel
        self.config_panel = ConfigurationPanel(parent, width=320, height=600)
        self.config_panel.pack(fill="both", expand=True, padx=10, pady=10)
    
    def setup_status_bar(self, parent):
        """Setup status bar at bottom."""
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Server listening on port 4446 - Waiting for CLI connection",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        # Threshold display (bottom right corner)
        self.threshold_display = ctk.CTkLabel(
            status_frame,
            text=f"Threshold: {self.current_threshold:.1f}°C",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ff6b6b"
        )
        self.threshold_display.pack(side="right", padx=10, pady=5)
        
        # Data rate indicator  
        self.data_rate_label = ctk.CTkLabel(
            status_frame,
            text="Data Rate: 0 Hz",
            font=ctk.CTkFont(size=12)
        )
        self.data_rate_label.pack(side="right", padx=10, pady=5)
    
    def setup_callbacks(self):
        """Setup callbacks between components."""
        # Configuration panel callbacks
        self.config_panel.set_threshold_callback(self.on_threshold_change)
        self.config_panel.set_sample_rate_callback(self.on_sample_rate_change)
        self.config_panel.set_connection_callback(self.on_connection_change)
    
    def on_threshold_change(self, threshold):
        """Handle threshold change from configuration panel."""
        self.current_threshold = threshold
        
        # Update dial threshold
        self.dial.set_threshold(threshold)
        
        # Update plot threshold
        self.plot.set_threshold(threshold)
        
        # Update threshold display in bottom right corner
        self.threshold_display.configure(
            text=f"Threshold: {threshold:.1f}°C"
        )
        logger.info(f"Threshold changed to {threshold:.1f}°C")
    
    def on_sample_rate_change(self, sample_rate):
        """Handle sample rate change from configuration panel."""
        logger.info(f"Sample rate changed to {sample_rate}ms")
    
    def on_connection_change(self, connected):
        """Handle connection state change."""
        if connected:
            self.connection_indicator.configure(
                text="Connected",
                text_color="white"
            )
            self.status_label.configure(
                text="Connected to SimTemp sensor - Ready to monitor"
            )
            
            # Create data client for real-time monitoring
            host = self.config_panel.host_entry.get()
            port = int(self.config_panel.port_entry.get())
            self.data_client = ExternalSimTempClient(host, port)
            
        else:
            self.connection_indicator.configure(
                text="Disconnected",
                text_color="white"
            )
            self.status_label.configure(
                text="Disconnected from sensor"
            )
            
            # Stop monitoring if active
            if self.monitoring_active:
                self.toggle_monitoring()
            
            self.data_client = None
    
    def toggle_monitoring(self):
        """Toggle real-time monitoring."""
        if not self.monitoring_active:
            # Start monitoring
            if self.data_client and self.data_client.connect():
                self.monitoring_active = True
                self.monitoring_button.configure(text="Stop Monitoring")
                
                # Set up data callback
                self.data_client.set_data_callback(self.on_new_data)
                
                # Start monitoring in background
                self.data_client.start_monitoring()
                
                # Start plot animation
                self.plot.start_animation(1000)
                
                self.status_label.configure(text="Monitoring active - Receiving data")
            else:
                # Use status message instead of modal dialog to avoid grab conflicts
                self.status_label.configure(text="Error: Failed to connect for monitoring")
                print("[ERROR] Failed to connect for monitoring")
        else:
            # Stop monitoring
            self.monitoring_active = False
            self.monitoring_button.configure(text="Start Monitoring")
            
            if self.data_client:
                self.data_client.stop_monitoring()
                self.data_client.disconnect()
            
            # Stop plot animation
            self.plot.stop_animation()
            
            self.status_label.configure(text="Monitoring stopped")
    
    def on_new_data(self, sample):
        """Handle new temperature data sample."""
        try:
            temperature = sample['temperature_celsius']
            self.current_temperature = temperature
            
            # Check alarm condition
            self.alarm_active = temperature >= self.current_threshold
            
            # Update GUI components in main thread
            self.root.after(0, self.update_temperature_display, temperature)
            
            # Add to plot
            self.plot.add_data_point(temperature)
            
        except Exception as e:
            logger.error(f"Error processing data sample: {e}")
    
    def update_temperature_display(self, temperature):
        """Update temperature display components."""
        # Update dial
        self.dial.set_temperature(temperature)
        
        # Update 7-segment display
        self.display.set_value(temperature, self.alarm_active)
        
        # Update statistics
        self.update_statistics()
        
        # Update alarm lamp
        if self.alarm_active:
            self.alarm_lamp.pack(side="right", padx=(0, 20), pady=15)
            self.alarm_lamp.configure(text="🔴")
        else:
            self.alarm_lamp.pack_forget()
    
    def update_statistics(self):
        """Update temperature statistics display."""
        if self.plot:
            stats = self.plot.get_current_stats()
            if stats:
                stats_text = f"Current: {stats['current']:.1f}°C\\n"
                stats_text += f"Min: {stats['min']:.1f}°C\\n"
                stats_text += f"Max: {stats['max']:.1f}°C\\n"
                stats_text += f"Average: {stats['avg']:.1f}°C\\n"
                stats_text += f"Samples: {stats['count']}"
                
                self.stats_text.delete("1.0", "end")
                self.stats_text.insert("1.0", stats_text)
    
    def clear_plot_data(self):
        """Clear plot data."""
        if self.plot:
            self.plot.clear_data()
            self.update_statistics()
    
    def export_plot_data(self):
        """Export plot data to CSV file."""
        if self.plot:
            try:
                from tkinter import filedialog
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                )
                if filename:
                    self.plot.export_data(filename)
                    self.status_label.configure(text=f"Data exported to {filename}")
            except Exception as e:
                # Handle grab conflicts or other dialog issues gracefully
                self.status_label.configure(text="Export failed - try again")
                logger.error(f"Export dialog error: {e}")
    
    def change_time_window(self, window_str):
        """Change plot time window."""
        window_map = {
            "1 min": 60,
            "5 min": 300,
            "10 min": 600,
            "30 min": 1800
        }
        
        if window_str in window_map:
            seconds = window_map[window_str]
            # Assume ~1 sample per second for data point calculation
            # This gives reasonable display windows
            max_points = max(60, seconds)  # Min 60 points, up to time window
            self.plot.set_max_points(max_points)
    
    def on_closing(self):
        """Handle application closing."""
        # Stop monitoring
        if self.monitoring_active:
            self.toggle_monitoring()
        
        # Disconnect from sensor
        if self.data_client:
            self.data_client.disconnect()
        
        # Stop CLI server
        if hasattr(self, 'cli_server'):
            self.cli_server.stop()
        
        self.root.quit()
        self.root.destroy()

    def on_cli_data_received(self, data):
        """Handle temperature data received from CLI"""
        try:
            temp_c = data.get('temperature_c', 0.0)
            timestamp = data.get('timestamp', time.time())
            
            # Show temperature sample clearly in console
            print(f"Temperature Sample: {temp_c:.1f}°C")
            
            # Rate limit GUI updates to prevent grab conflicts
            current_time = time.time()
            if current_time - self.last_gui_update >= self.gui_update_interval:
                self.last_gui_update = current_time
                # Update temperature in main thread with error handling
                try:
                    self.root.after(0, self._update_temperature_display, temp_c, timestamp)
                except Exception as e:
                    logger.error(f"Error scheduling GUI update: {e}")
            
        except Exception as e:
            logger.error(f"Error processing CLI data: {e}")

    def on_cli_connection_change(self, connected, addr=None):
        """Handle CLI connection state change"""
        try:
            if connected:
                status_text = f"✓ CLI client connected from {addr[0]}:{addr[1]}"
                self.root.after(0, self._update_connection_status, True, status_text)
            else:
                status_text = "✗ CLI client disconnected - Waiting for reconnection"
                self.root.after(0, self._update_connection_status, False, status_text)
        except Exception as e:
            logger.error(f"Error handling CLI connection change: {e}")

    def _update_connection_status(self, connected, status_text):
        """Update connection status in main thread"""
        try:
            # Prevent grab conflicts by checking if there's an active grab
            if self.root.grab_current() is not None:
                # Reschedule if there's an active grab
                self.root.after(100, self._update_connection_status, connected, status_text)
                return
                
            if connected:
                self.connection_indicator.configure(
                    text="✓ GUI Client Connected",
                    text_color="lightgreen"
                )
                self.status_label.configure(text=status_text)
            else:
                self.connection_indicator.configure(
                    text="⏳ Waiting for CLI connection",
                    text_color="yellow"
                )
                self.status_label.configure(
                    text="Server listening on port 4446 - Waiting for CLI connection"
                )
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")

    def _update_temperature_display(self, temperature, timestamp=None):
        """Update GUI with new temperature data (runs in main thread)"""
        try:
            # Prevent grab conflicts by checking if there's an active grab
            if self.root.grab_current() is not None:
                # Reschedule if there's an active grab to avoid conflicts
                self.root.after(50, self._update_temperature_display, temperature, timestamp)
                return
                
            self.current_temperature = temperature
            
            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = datetime.now()
            elif isinstance(timestamp, (int, float)):
                # Convert Unix timestamp to datetime
                timestamp = datetime.fromtimestamp(timestamp)
            
            # Update dial
            if self.dial and hasattr(self.dial, 'set_temperature'):
                try:
                    self.dial.set_temperature(temperature)
                except Exception as e:
                    logger.error(f"Error updating dial: {e}")
            
            # Update display
            if self.display and hasattr(self.display, 'set_value'):
                try:
                    self.display.set_value(f"{temperature:.1f}")
                except Exception as e:
                    logger.error(f"Error updating display: {e}")
            
            # Update plot
            if self.plot and hasattr(self.plot, 'add_data_point'):
                try:
                    # Use the actual timestamp from the data
                    self.plot.add_data_point(temperature, timestamp=timestamp)
                except Exception as e:
                    logger.error(f"Error updating plot: {e}")
            
            # Check threshold
            if temperature > self.current_threshold:
                if not self.alarm_active:
                    self.alarm_active = True
                    print(f"🚨 ALARM: Temperature {temperature:.1f}°C exceeds "
                          f"threshold {self.current_threshold:.1f}°C")
            else:
                self.alarm_active = False
                
        except Exception as e:
            logger.error(f"Error in _update_temperature_display: {e}")

    def run(self):
        """Start the GUI application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"Application error: {e}")


def main():
    """Main entry point."""
    print("SimTemp External GUI Application")
    print("Challenge 2025 - Temperature Sensor Monitor")
    print("=" * 50)
    
    # Check if running in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and
                                       sys.base_prefix != sys.prefix):
        print("✓ Running in virtual environment")
    else:
        print("⚠ Not running in virtual environment")
    
    # Check dependencies
    try:
        import customtkinter
        import matplotlib
        print("✓ Dependencies available")
    except ImportError as e:
        print(f"✗ Missing dependencies: {e}")
        return 1
    
    print("Starting GUI application...")
    
    # Create and run application
    app = SimTempExternalGUI()
    app.run()
    
    return 0


if __name__ == "__main__":
    exit(main())
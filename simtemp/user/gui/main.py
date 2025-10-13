#!/usr/bin/env python3
"""
Challenge 2025 Temperature Sensor GUI Application

Real-time temperature monitoring GUI with Seaborn visualization,
threshold controls, and alert monitoring for the Challenge 2025 sensor system.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import logging
from datetime import datetime, timedelta
import sys
import os

# Add CLI path for importing sensor modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cli'))

try:
    from simtemp_reader import SimtempReader
    from sysfs_config import SysfsConfig
except ImportError as e:
    print(f"Error importing sensor modules: {e}")
    print("Make sure the CLI modules are available")
    sys.exit(1)

# Import visualization components
from temperature_dashboard import TemperatureDashboard
from control_panel import ControlPanel
from alert_monitor import AlertMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemperatureSensorGUI:
    """Main GUI application for Challenge 2025 temperature sensor monitoring."""
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Challenge 2025 Temperature Sensor Monitor")
        self.root.geometry("1200x800")
        
        # Initialize sensor interfaces
        self.device_path = "/dev/simtemp"
        self.sysfs_base = "/sys/class/misc/simtemp"
        self.config = None
        self.reader = None
        
        # Threading and data management
        self.data_queue = queue.Queue()
        self.running = False
        self.reader_thread = None
        
        # Data storage for visualization
        self.max_data_points = 1000
        self.temperature_data = []
        self.timestamp_data = []
        self.alert_events = []
        
        # Initialize GUI components
        self.setup_gui()
        self.setup_sensor_interfaces()
        
        # Bind cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_gui(self):
        """Setup the main GUI layout and components."""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Temperature Dashboard")
        self.dashboard = TemperatureDashboard(dashboard_frame)
        
        # Control tab
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Control Panel")
        self.control_panel = ControlPanel(control_frame, self.on_config_change)
        
        # Alerts tab
        alerts_frame = ttk.Frame(self.notebook)
        self.notebook.add(alerts_frame, text="Alert Monitor")
        self.alert_monitor = AlertMonitor(alerts_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
        
        # Menu bar
        self.setup_menu_bar()
    
    def setup_status_bar(self, parent):
        """Setup status bar at bottom of window."""
        status_frame = ttk.Frame(parent)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Initializing...")
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Connection indicator
        self.connection_var = tk.StringVar()
        self.connection_var.set("Disconnected")
        
        connection_label = ttk.Label(status_frame, textvariable=self.connection_var,
                                   relief=tk.SUNKEN, width=15)
        connection_label.pack(side=tk.RIGHT)
    
    def setup_menu_bar(self):
        """Setup application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Data...", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Sensor menu
        sensor_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sensor", menu=sensor_menu)
        sensor_menu.add_command(label="Connect", command=self.connect_sensor)
        sensor_menu.add_command(label="Disconnect", command=self.disconnect_sensor)
        sensor_menu.add_separator()
        sensor_menu.add_command(label="Reset Configuration", command=self.reset_config)
        sensor_menu.add_command(label="Run Test", command=self.run_test)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_sensor_interfaces(self):
        """Initialize sensor configuration and reader interfaces."""
        try:
            self.config = SysfsConfig(self.sysfs_base)
            self.reader = SimtempReader(self.device_path)
            
            # Validate sensor access
            access_status = self.config.validate_sysfs_access()
            device_info = self.reader.get_device_info()
            
            if not device_info.get('exists', False):
                self.status_var.set("Warning: Sensor device not found")
                logger.warning(f"Device {self.device_path} not found")
            else:
                self.status_var.set("Sensor interfaces initialized")
                logger.info("Sensor interfaces initialized successfully")
            
            # Update control panel with current configuration
            self.update_control_panel()
            
        except Exception as e:
            error_msg = f"Failed to initialize sensor interfaces: {e}"
            self.status_var.set(error_msg)
            logger.error(error_msg)
            messagebox.showerror("Initialization Error", error_msg)
    
    def update_control_panel(self):
        """Update control panel with current sensor configuration."""
        if self.config:
            try:
                current_config = self.config.get_current_config()
                self.control_panel.update_configuration(current_config)
            except Exception as e:
                logger.error(f"Failed to update control panel: {e}")
    
    def on_config_change(self, config_changes):
        """Handle configuration changes from control panel."""
        if not self.config:
            messagebox.showerror("Error", "Sensor not initialized")
            return
        
        try:
            results = self.config.set_config(**config_changes)
            failed_items = [k for k, v in results.items() if not v]
            
            if failed_items:
                error_msg = f"Failed to set configuration for: {', '.join(failed_items)}"
                messagebox.showerror("Configuration Error", error_msg)
                logger.error(error_msg)
            else:
                self.status_var.set(f"Configuration updated: {', '.join(config_changes.keys())}")
                logger.info(f"Configuration updated: {config_changes}")
                
        except Exception as e:
            error_msg = f"Error updating configuration: {e}"
            messagebox.showerror("Configuration Error", error_msg)
            logger.error(error_msg)
    
    def connect_sensor(self):
        """Connect to sensor and start data acquisition."""
        if self.running:
            messagebox.showwarning("Warning", "Sensor already connected")
            return
        
        try:
            if not self.reader.open():
                messagebox.showerror("Connection Error", "Failed to open sensor device")
                return
            
            self.running = True
            self.reader_thread = threading.Thread(target=self.data_reader_loop, daemon=True)
            self.reader_thread.start()
            
            # Start GUI update timer
            self.root.after(100, self.update_gui_data)
            
            self.connection_var.set("Connected")
            self.status_var.set("Sensor connected and monitoring")
            logger.info("Sensor connected successfully")
            
        except Exception as e:
            error_msg = f"Failed to connect to sensor: {e}"
            messagebox.showerror("Connection Error", error_msg)
            logger.error(error_msg)
    
    def disconnect_sensor(self):
        """Disconnect from sensor and stop data acquisition."""
        if not self.running:
            messagebox.showwarning("Warning", "Sensor not connected")
            return
        
        self.running = False
        
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2.0)
        
        if self.reader:
            self.reader.close()
        
        self.connection_var.set("Disconnected")
        self.status_var.set("Sensor disconnected")
        logger.info("Sensor disconnected")
    
    def data_reader_loop(self):
        """Background thread loop for reading sensor data."""
        logger.info("Data reader loop started")
        
        while self.running:
            try:
                sample = self.reader.read_sample(timeout_ms=1000)
                if sample:
                    # Add timestamp for GUI
                    sample['gui_timestamp'] = time.time()
                    self.data_queue.put(sample)
                else:
                    # No data received - check if we should continue
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in data reader loop: {e}")
                # Put error in queue for GUI handling
                self.data_queue.put({'error': str(e)})
                break
        
        logger.info("Data reader loop stopped")
    
    def update_gui_data(self):
        """Update GUI with new sensor data (called periodically)."""
        if not self.running:
            return
        
        # Process all queued data
        new_samples = []
        while not self.data_queue.empty():
            try:
                item = self.data_queue.get_nowait()
                
                if 'error' in item:
                    self.status_var.set(f"Sensor error: {item['error']}")
                    logger.error(f"Sensor error: {item['error']}")
                    self.disconnect_sensor()
                    return
                
                new_samples.append(item)
                
            except queue.Empty:
                break
        
        # Update data storage
        for sample in new_samples:
            self.add_sample_to_storage(sample)
        
        # Update GUI components
        if new_samples:
            self.update_dashboard()
            self.update_alert_monitor(new_samples)
            
            # Update status with latest sample
            latest = new_samples[-1]
            temp_c = latest['temp_mC'] / 1000.0
            alert_status = "ALERT" if latest.get('threshold_crossed', False) else "OK"
            self.status_var.set(f"Temperature: {temp_c:.1f}°C | Status: {alert_status}")
        
        # Schedule next update
        self.root.after(100, self.update_gui_data)
    
    def add_sample_to_storage(self, sample):
        """Add sample to internal data storage for visualization."""
        # Convert timestamp to datetime
        timestamp = datetime.fromtimestamp(sample['timestamp_ns'] / 1e9)
        temp_c = sample['temp_mC'] / 1000.0
        
        self.timestamp_data.append(timestamp)
        self.temperature_data.append(temp_c)
        
        # Check for alerts
        if sample.get('threshold_crossed', False):
            alert_event = {
                'timestamp': timestamp,
                'temperature': temp_c,
                'type': 'threshold_crossed'
            }
            self.alert_events.append(alert_event)
        
        # Maintain maximum data points
        if len(self.temperature_data) > self.max_data_points:
            self.timestamp_data.pop(0)
            self.temperature_data.pop(0)
        
        # Clean old alert events (keep last 100)
        if len(self.alert_events) > 100:
            self.alert_events.pop(0)
    
    def update_dashboard(self):
        """Update the temperature dashboard with new data."""
        if self.temperature_data and self.timestamp_data:
            self.dashboard.update_temperature_plot(
                self.timestamp_data, 
                self.temperature_data,
                self.alert_events
            )
    
    def update_alert_monitor(self, new_samples):
        """Update alert monitor with new samples."""
        alert_samples = [s for s in new_samples if s.get('threshold_crossed', False)]
        if alert_samples:
            self.alert_monitor.add_alerts(alert_samples)
    
    def export_data(self):
        """Export collected temperature data to file."""
        if not self.temperature_data:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                title="Export Temperature Data",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                self._export_data_to_file(filename)
                messagebox.showinfo("Export Complete", f"Data exported to {filename}")
                
        except Exception as e:
            error_msg = f"Failed to export data: {e}"
            messagebox.showerror("Export Error", error_msg)
            logger.error(error_msg)
    
    def _export_data_to_file(self, filename):
        """Export data to CSV file."""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'Temperature_C', 'Alert'])
            
            for i, (timestamp, temp) in enumerate(zip(self.timestamp_data, self.temperature_data)):
                # Check if this timestamp has an alert
                alert = any(abs((alert['timestamp'] - timestamp).total_seconds()) < 1.0 
                           for alert in self.alert_events)
                
                writer.writerow([timestamp.isoformat(), f"{temp:.3f}", int(alert)])
    
    def reset_config(self):
        """Reset sensor configuration to defaults."""
        if not self.config:
            messagebox.showerror("Error", "Sensor not initialized")
            return
        
        if messagebox.askyesno("Confirm Reset", "Reset sensor configuration to defaults?"):
            try:
                if self.config.reset_to_defaults():
                    self.update_control_panel()
                    self.status_var.set("Configuration reset to defaults")
                    messagebox.showinfo("Success", "Configuration reset successfully")
                else:
                    messagebox.showerror("Error", "Failed to reset configuration")
                    
            except Exception as e:
                error_msg = f"Error resetting configuration: {e}"
                messagebox.showerror("Reset Error", error_msg)
                logger.error(error_msg)
    
    def run_test(self):
        """Run sensor test mode."""
        if not self.config or not self.reader:
            messagebox.showerror("Error", "Sensor not initialized")
            return
        
        # Import test mode
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cli'))
            from test_mode import TestMode
            
            def run_test_thread():
                test = TestMode(self.config, self.reader)
                result = test.run_threshold_test(test_duration=20.0)
                
                # Show result in main thread
                self.root.after(0, lambda: self.show_test_result(result))
            
            # Run test in background
            test_thread = threading.Thread(target=run_test_thread, daemon=True)
            test_thread.start()
            
            messagebox.showinfo("Test Started", "Threshold test started. Check status bar for progress.")
            
        except Exception as e:
            error_msg = f"Failed to run test: {e}"
            messagebox.showerror("Test Error", error_msg)
            logger.error(error_msg)
    
    def show_test_result(self, result):
        """Show test result to user."""
        if result:
            messagebox.showinfo("Test Result", "Test PASSED: Threshold crossing detected successfully")
        else:
            messagebox.showerror("Test Result", "Test FAILED: No valid threshold crossing detected")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """Challenge 2025 Temperature Sensor Monitor

A real-time temperature monitoring application with:
• Live temperature visualization using Seaborn
• Configurable sampling period and thresholds
• Alert monitoring and logging
• Data export capabilities

Developed for the Challenge 2025 Systems Software requirements."""
        
        messagebox.showinfo("About", about_text)
    
    def on_closing(self):
        """Handle application closing."""
        if self.running:
            if messagebox.askyesno("Confirm Exit", "Sensor is still connected. Disconnect and exit?"):
                self.disconnect_sensor()
            else:
                return
        
        logger.info("Application closing")
        self.root.destroy()


def main():
    """Main entry point for the GUI application."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and run application
    root = tk.Tk()
    
    try:
        app = TemperatureSensorGUI(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Application Error", f"An error occurred: {e}")


if __name__ == "__main__":
    main()
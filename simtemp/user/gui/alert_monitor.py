#!/usr/bin/env python3
"""
Alert monitor widget for temperature sensor alerts and notifications.
Displays real-time alerts, alert history, and provides alert management.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from collections import deque
import queue


class AlertLevel:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TemperatureAlert:
    """Temperature alert data structure."""
    
    def __init__(self, level: str, message: str, temperature: float, timestamp: Optional[datetime] = None):
        """
        Initialize a temperature alert.
        
        Args:
            level: Alert level (info, warning, critical)
            message: Alert message
            temperature: Temperature value that triggered the alert
            timestamp: Alert timestamp (defaults to now)
        """
        self.level = level
        self.message = message
        self.temperature = temperature
        self.timestamp = timestamp or datetime.now()
        self.acknowledged = False
        self.id = f"{self.timestamp.strftime('%Y%m%d_%H%M%S')}_{id(self)}"
    
    def __str__(self):
        return f"[{self.level.upper()}] {self.timestamp.strftime('%H:%M:%S')} - {self.message} ({self.temperature:.1f}°C)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'temperature': self.temperature,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }


class AlertMonitor(ttk.Frame):
    """Alert monitor widget for displaying and managing temperature alerts."""
    
    def __init__(self, parent, alert_callback: Optional[Callable] = None):
        """
        Initialize the alert monitor.
        
        Args:
            parent: Parent widget
            alert_callback: Callback function for alert actions
        """
        super().__init__(parent)
        self.alert_callback = alert_callback
        self.logger = logging.getLogger(__name__)
        
        # Alert storage
        self.alerts = deque(maxlen=1000)  # Keep last 1000 alerts
        self.alert_queue = queue.Queue()
        self.active_alerts = []  # Unacknowledged alerts
        
        # Configuration
        self.config = {
            'auto_acknowledge_timeout': 30,  # seconds
            'max_visible_alerts': 100,
            'enable_sound': True,
            'enable_notifications': True
        }
        
        # State
        self.monitoring_enabled = True
        self.alert_counts = {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 0,
            AlertLevel.CRITICAL: 0
        }
        
        self.setup_ui()
        self.setup_alert_processor()
    
    def setup_ui(self):
        """Set up the alert monitor user interface."""
        # Main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Active alerts tab
        self.setup_active_alerts_tab()
        
        # Alert history tab
        self.setup_history_tab()
        
        # Alert settings tab
        self.setup_settings_tab()
        
        # Status bar
        self.setup_status_bar()
    
    def setup_active_alerts_tab(self):
        """Set up the active alerts tab."""
        active_frame = ttk.Frame(self.notebook)
        self.notebook.add(active_frame, text="Active Alerts")
        
        # Alert summary
        summary_frame = ttk.LabelFrame(active_frame, text="Alert Summary", padding="5")
        summary_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # Alert counters
        counters_frame = ttk.Frame(summary_frame)
        counters_frame.pack(fill="x")
        
        # Critical alerts
        self.critical_var = tk.StringVar(value="0")
        critical_frame = ttk.Frame(counters_frame)
        critical_frame.pack(side="left", padx=(0, 10))
        ttk.Label(critical_frame, text="Critical:", foreground="red").pack(side="left")
        ttk.Label(critical_frame, textvariable=self.critical_var, foreground="red", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(5, 0))
        
        # Warning alerts
        self.warning_var = tk.StringVar(value="0")
        warning_frame = ttk.Frame(counters_frame)
        warning_frame.pack(side="left", padx=(0, 10))
        ttk.Label(warning_frame, text="Warning:", foreground="orange").pack(side="left")
        ttk.Label(warning_frame, textvariable=self.warning_var, foreground="orange", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(5, 0))
        
        # Info alerts
        self.info_var = tk.StringVar(value="0")
        info_frame = ttk.Frame(counters_frame)
        info_frame.pack(side="left")
        ttk.Label(info_frame, text="Info:", foreground="blue").pack(side="left")
        ttk.Label(info_frame, textvariable=self.info_var, foreground="blue", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(5, 0))
        
        # Alert list
        list_frame = ttk.LabelFrame(active_frame, text="Active Alerts", padding="5")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Treeview for active alerts
        columns = ("Time", "Level", "Message", "Temperature")
        self.active_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.active_tree.heading("Time", text="Time")
        self.active_tree.heading("Level", text="Level")
        self.active_tree.heading("Message", text="Message")
        self.active_tree.heading("Temperature", text="Temperature (°C)")
        
        self.active_tree.column("Time", width=80, anchor="center")
        self.active_tree.column("Level", width=80, anchor="center")
        self.active_tree.column("Message", width=250, anchor="w")
        self.active_tree.column("Temperature", width=100, anchor="center")
        
        # Scrollbars for active alerts
        active_v_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.active_tree.yview)
        active_h_scroll = ttk.Scrollbar(list_frame, orient="horizontal", command=self.active_tree.xview)
        self.active_tree.configure(yscrollcommand=active_v_scroll.set, xscrollcommand=active_h_scroll.set)
        
        # Pack active alerts treeview
        self.active_tree.grid(row=0, column=0, sticky="nsew")
        active_v_scroll.grid(row=0, column=1, sticky="ns")
        active_h_scroll.grid(row=1, column=0, sticky="ew")
        
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        
        # Alert actions
        actions_frame = ttk.Frame(active_frame)
        actions_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        ttk.Button(actions_frame, text="Acknowledge Selected", command=self.acknowledge_selected).pack(side="left", padx=(0, 5))
        ttk.Button(actions_frame, text="Acknowledge All", command=self.acknowledge_all).pack(side="left", padx=(0, 5))
        ttk.Button(actions_frame, text="Clear Acknowledged", command=self.clear_acknowledged).pack(side="left", padx=(0, 5))
        ttk.Button(actions_frame, text="Export Alerts", command=self.export_alerts).pack(side="right")
    
    def setup_history_tab(self):
        """Set up the alert history tab."""
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="History")
        
        # History filters
        filter_frame = ttk.LabelFrame(history_frame, text="Filters", padding="5")
        filter_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        filters_grid = ttk.Frame(filter_frame)
        filters_grid.pack(fill="x")
        
        # Time range filter
        ttk.Label(filters_grid, text="Time Range:").grid(row=0, column=0, sticky="w")
        self.time_range_var = tk.StringVar(value="Last 24 Hours")
        time_combo = ttk.Combobox(filters_grid, textvariable=self.time_range_var, 
                                  values=["Last Hour", "Last 24 Hours", "Last 7 Days", "All"], 
                                  state="readonly", width=15)
        time_combo.grid(row=0, column=1, sticky="w", padx=(5, 10))
        time_combo.bind("<<ComboboxSelected>>", self.filter_history)
        
        # Level filter
        ttk.Label(filters_grid, text="Level:").grid(row=0, column=2, sticky="w")
        self.level_filter_var = tk.StringVar(value="All")
        level_combo = ttk.Combobox(filters_grid, textvariable=self.level_filter_var,
                                   values=["All", "Critical", "Warning", "Info"],
                                   state="readonly", width=10)
        level_combo.grid(row=0, column=3, sticky="w", padx=(5, 10))
        level_combo.bind("<<ComboboxSelected>>", self.filter_history)
        
        # Refresh button
        ttk.Button(filters_grid, text="Refresh", command=self.refresh_history).grid(row=0, column=4, sticky="w", padx=(5, 0))
        
        # History list
        history_list_frame = ttk.LabelFrame(history_frame, text="Alert History", padding="5")
        history_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Treeview for history
        columns = ("Time", "Level", "Message", "Temperature")
        self.history_tree = ttk.Treeview(history_list_frame, columns=columns, show="headings", height=12)
        
        # Configure columns (same as active alerts)
        for col in columns:
            self.history_tree.heading(col, text=col)
        
        self.history_tree.column("Time", width=120, anchor="center")
        self.history_tree.column("Level", width=80, anchor="center")
        self.history_tree.column("Message", width=300, anchor="w")
        self.history_tree.column("Temperature", width=100, anchor="center")
        
        # Scrollbars for history
        history_v_scroll = ttk.Scrollbar(history_list_frame, orient="vertical", command=self.history_tree.yview)
        history_h_scroll = ttk.Scrollbar(history_list_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=history_v_scroll.set, xscrollcommand=history_h_scroll.set)
        
        # Pack history treeview
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        history_v_scroll.grid(row=0, column=1, sticky="ns")
        history_h_scroll.grid(row=1, column=0, sticky="ew")
        
        history_list_frame.rowconfigure(0, weight=1)
        history_list_frame.columnconfigure(0, weight=1)
    
    def setup_settings_tab(self):
        """Set up the alert settings tab."""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Alert preferences
        prefs_frame = ttk.LabelFrame(settings_frame, text="Alert Preferences", padding="10")
        prefs_frame.pack(fill="x", padx=5, pady=5)
        
        # Sound notifications
        self.sound_var = tk.BooleanVar(value=self.config['enable_sound'])
        ttk.Checkbutton(prefs_frame, text="Enable sound notifications", variable=self.sound_var,
                       command=self.update_sound_setting).pack(anchor="w")
        
        # Desktop notifications
        self.notifications_var = tk.BooleanVar(value=self.config['enable_notifications'])
        ttk.Checkbutton(prefs_frame, text="Enable desktop notifications", variable=self.notifications_var,
                       command=self.update_notifications_setting).pack(anchor="w", pady=(5, 0))
        
        # Auto-acknowledge timeout
        timeout_frame = ttk.Frame(prefs_frame)
        timeout_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(timeout_frame, text="Auto-acknowledge timeout (seconds):").pack(side="left")
        self.timeout_var = tk.StringVar(value=str(self.config['auto_acknowledge_timeout']))
        timeout_spinbox = ttk.Spinbox(timeout_frame, from_=0, to=300, increment=5,
                                     textvariable=self.timeout_var, width=10,
                                     command=self.update_timeout_setting)
        timeout_spinbox.pack(side="left", padx=(5, 0))
        
        # Alert management
        mgmt_frame = ttk.LabelFrame(settings_frame, text="Alert Management", padding="10")
        mgmt_frame.pack(fill="x", padx=5, pady=5)
        
        # Management buttons
        mgmt_buttons = ttk.Frame(mgmt_frame)
        mgmt_buttons.pack(fill="x")
        
        ttk.Button(mgmt_buttons, text="Clear All Alerts", command=self.clear_all_alerts).pack(side="left", padx=(0, 5))
        ttk.Button(mgmt_buttons, text="Test Alert", command=self.test_alert).pack(side="left", padx=(0, 5))
        ttk.Button(mgmt_buttons, text="Export Configuration", command=self.export_config).pack(side="left")
        
        # Alert statistics
        stats_frame = ttk.LabelFrame(settings_frame, text="Statistics", padding="10")
        stats_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=8, state="disabled")
        stats_scroll = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scroll.set)
        
        self.stats_text.pack(side="left", fill="both", expand=True)
        stats_scroll.pack(side="right", fill="y")
        
        self.update_statistics()
    
    def setup_status_bar(self):
        """Set up the status bar."""
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", side="bottom")
        
        # Monitoring status
        self.monitoring_var = tk.StringVar(value="Monitoring: ON")
        monitoring_label = ttk.Label(status_frame, textvariable=self.monitoring_var)
        monitoring_label.pack(side="left", padx=5)
        
        # Toggle monitoring
        self.toggle_button = ttk.Button(status_frame, text="Disable Monitoring", command=self.toggle_monitoring)
        self.toggle_button.pack(side="right", padx=5)
        
        # Last alert time
        self.last_alert_var = tk.StringVar(value="Last alert: None")
        last_alert_label = ttk.Label(status_frame, textvariable=self.last_alert_var)
        last_alert_label.pack(side="right", padx=(0, 10))
    
    def setup_alert_processor(self):
        """Set up the background alert processor."""
        def process_alerts():
            while True:
                try:
                    # Process queued alerts
                    while not self.alert_queue.empty():
                        alert = self.alert_queue.get_nowait()
                        self.process_alert(alert)
                    
                    # Check for auto-acknowledgment
                    self.check_auto_acknowledge()
                    
                    time.sleep(1)  # Check every second
                    
                except Exception as e:
                    self.logger.error(f"Alert processor error: {e}")
        
        # Start processor thread
        processor_thread = threading.Thread(target=process_alerts, daemon=True)
        processor_thread.start()
    
    def add_alert(self, level: str, message: str, temperature: float):
        """
        Add a new alert to the queue.
        
        Args:
            level: Alert level (info, warning, critical)
            message: Alert message
            temperature: Temperature value
        """
        if not self.monitoring_enabled:
            return
        
        alert = TemperatureAlert(level, message, temperature)
        self.alert_queue.put(alert)
    
    def process_alert(self, alert: TemperatureAlert):
        """
        Process a new alert.
        
        Args:
            alert: Alert to process
        """
        try:
            # Add to storage
            self.alerts.append(alert)
            self.active_alerts.append(alert)
            
            # Update counters
            self.alert_counts[alert.level] += 1
            self.update_counters()
            
            # Update display
            self.after(0, lambda: self.add_alert_to_tree(alert))
            
            # Update last alert time
            self.last_alert_var.set(f"Last alert: {alert.timestamp.strftime('%H:%M:%S')}")
            
            # Handle notifications
            if self.config['enable_notifications']:
                self.show_notification(alert)
            
            if self.config['enable_sound']:
                self.play_alert_sound(alert.level)
            
            self.logger.info(f"Alert processed: {alert}")
            
        except Exception as e:
            self.logger.error(f"Error processing alert: {e}")
    
    def add_alert_to_tree(self, alert: TemperatureAlert):
        """Add alert to the active alerts tree."""
        # Determine row color based on level
        tags = []
        if alert.level == AlertLevel.CRITICAL:
            tags = ["critical"]
        elif alert.level == AlertLevel.WARNING:
            tags = ["warning"]
        else:
            tags = ["info"]
        
        # Configure tags
        self.active_tree.tag_configure("critical", background="#ffcccc")
        self.active_tree.tag_configure("warning", background="#fff3cd")
        self.active_tree.tag_configure("info", background="#d4edda")
        
        # Insert alert
        item = self.active_tree.insert("", 0, values=(
            alert.timestamp.strftime("%H:%M:%S"),
            alert.level.upper(),
            alert.message,
            f"{alert.temperature:.1f}"
        ), tags=tags)
        
        # Store alert reference
        self.active_tree.set(item, "alert_id", alert.id)
    
    def acknowledge_selected(self):
        """Acknowledge selected alerts."""
        selection = self.active_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select alerts to acknowledge.")
            return
        
        acknowledged_count = 0
        for item in selection:
            alert_id = self.active_tree.set(item, "alert_id")
            for alert in self.active_alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    acknowledged_count += 1
                    break
        
        self.refresh_active_alerts()
        messagebox.showinfo("Alerts Acknowledged", f"Acknowledged {acknowledged_count} alert(s).")
    
    def acknowledge_all(self):
        """Acknowledge all active alerts."""
        count = len([a for a in self.active_alerts if not a.acknowledged])
        if count == 0:
            messagebox.showinfo("No Alerts", "No alerts to acknowledge.")
            return
        
        for alert in self.active_alerts:
            alert.acknowledged = True
        
        self.refresh_active_alerts()
        messagebox.showinfo("Alerts Acknowledged", f"Acknowledged {count} alert(s).")
    
    def clear_acknowledged(self):
        """Remove acknowledged alerts from active list."""
        before_count = len(self.active_alerts)
        self.active_alerts = [a for a in self.active_alerts if not a.acknowledged]
        cleared_count = before_count - len(self.active_alerts)
        
        self.refresh_active_alerts()
        self.update_counters()
        
        if cleared_count > 0:
            messagebox.showinfo("Alerts Cleared", f"Cleared {cleared_count} acknowledged alert(s).")
    
    def clear_all_alerts(self):
        """Clear all alerts after confirmation."""
        if messagebox.askyesno("Clear All Alerts", "Are you sure you want to clear all alerts?"):
            self.alerts.clear()
            self.active_alerts.clear()
            self.alert_counts = {level: 0 for level in self.alert_counts}
            
            self.refresh_active_alerts()
            self.refresh_history()
            self.update_counters()
            self.update_statistics()
            
            messagebox.showinfo("Alerts Cleared", "All alerts have been cleared.")
    
    def refresh_active_alerts(self):
        """Refresh the active alerts display."""
        # Clear tree
        for item in self.active_tree.get_children():
            self.active_tree.delete(item)
        
        # Add unacknowledged alerts
        for alert in self.active_alerts:
            if not alert.acknowledged:
                self.add_alert_to_tree(alert)
    
    def refresh_history(self):
        """Refresh the alert history display."""
        # Clear history tree
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Filter alerts based on settings
        filtered_alerts = self.filter_alerts_by_criteria()
        
        # Add filtered alerts to history
        for alert in filtered_alerts:
            tags = [alert.level]
            self.history_tree.tag_configure("critical", background="#ffcccc")
            self.history_tree.tag_configure("warning", background="#fff3cd")
            self.history_tree.tag_configure("info", background="#d4edda")
            
            self.history_tree.insert("", "end", values=(
                alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                alert.level.upper(),
                alert.message,
                f"{alert.temperature:.1f}"
            ), tags=tags)
    
    def filter_alerts_by_criteria(self) -> List[TemperatureAlert]:
        """Filter alerts based on current filter criteria."""
        filtered = list(self.alerts)
        
        # Time range filter
        time_range = self.time_range_var.get()
        now = datetime.now()
        
        if time_range == "Last Hour":
            cutoff = now - timedelta(hours=1)
            filtered = [a for a in filtered if a.timestamp >= cutoff]
        elif time_range == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
            filtered = [a for a in filtered if a.timestamp >= cutoff]
        elif time_range == "Last 7 Days":
            cutoff = now - timedelta(days=7)
            filtered = [a for a in filtered if a.timestamp >= cutoff]
        
        # Level filter
        level_filter = self.level_filter_var.get()
        if level_filter != "All":
            filtered = [a for a in filtered if a.level == level_filter.lower()]
        
        return sorted(filtered, key=lambda a: a.timestamp, reverse=True)
    
    def filter_history(self, event=None):
        """Handle history filter changes."""
        self.refresh_history()
    
    def update_counters(self):
        """Update alert counters display."""
        # Count unacknowledged alerts by level
        counts = {AlertLevel.INFO: 0, AlertLevel.WARNING: 0, AlertLevel.CRITICAL: 0}
        for alert in self.active_alerts:
            if not alert.acknowledged:
                counts[alert.level] += 1
        
        self.critical_var.set(str(counts[AlertLevel.CRITICAL]))
        self.warning_var.set(str(counts[AlertLevel.WARNING]))
        self.info_var.set(str(counts[AlertLevel.INFO]))
    
    def update_statistics(self):
        """Update alert statistics display."""
        if not hasattr(self, 'stats_text'):
            return
        
        stats = []
        stats.append(f"Total alerts: {len(self.alerts)}")
        stats.append(f"Active alerts: {len([a for a in self.active_alerts if not a.acknowledged])}")
        stats.append(f"Critical alerts: {self.alert_counts[AlertLevel.CRITICAL]}")
        stats.append(f"Warning alerts: {self.alert_counts[AlertLevel.WARNING]}")
        stats.append(f"Info alerts: {self.alert_counts[AlertLevel.INFO]}")
        
        if self.alerts:
            latest = max(self.alerts, key=lambda a: a.timestamp)
            stats.append(f"Latest alert: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        stats.append(f"Monitoring: {'Enabled' if self.monitoring_enabled else 'Disabled'}")
        
        self.stats_text.configure(state="normal")
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, "\n".join(stats))
        self.stats_text.configure(state="disabled")
    
    def check_auto_acknowledge(self):
        """Check for alerts that should be auto-acknowledged."""
        timeout = self.config['auto_acknowledge_timeout']
        if timeout <= 0:
            return
        
        cutoff = datetime.now() - timedelta(seconds=timeout)
        acknowledged_count = 0
        
        for alert in self.active_alerts:
            if not alert.acknowledged and alert.timestamp < cutoff:
                alert.acknowledged = True
                acknowledged_count += 1
        
        if acknowledged_count > 0:
            self.after(0, self.refresh_active_alerts)
    
    def toggle_monitoring(self):
        """Toggle alert monitoring on/off."""
        self.monitoring_enabled = not self.monitoring_enabled
        
        if self.monitoring_enabled:
            self.monitoring_var.set("Monitoring: ON")
            self.toggle_button.configure(text="Disable Monitoring")
        else:
            self.monitoring_var.set("Monitoring: OFF")
            self.toggle_button.configure(text="Enable Monitoring")
        
        self.logger.info(f"Alert monitoring {'enabled' if self.monitoring_enabled else 'disabled'}")
    
    def test_alert(self):
        """Generate a test alert."""
        import random
        
        levels = [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.CRITICAL]
        level = random.choice(levels)
        temp = random.uniform(15.0, 85.0)
        
        messages = {
            AlertLevel.INFO: f"Temperature reading: {temp:.1f}°C",
            AlertLevel.WARNING: f"Temperature approaching threshold: {temp:.1f}°C",
            AlertLevel.CRITICAL: f"Temperature exceeds critical threshold: {temp:.1f}°C"
        }
        
        self.add_alert(level, messages[level], temp)
        messagebox.showinfo("Test Alert", f"Generated test {level} alert")
    
    def show_notification(self, alert: TemperatureAlert):
        """Show desktop notification for alert."""
        # This would typically use a system notification library
        # For now, just log the notification
        self.logger.info(f"Notification: {alert}")
    
    def play_alert_sound(self, level: str):
        """Play alert sound based on level."""
        # This would typically play a system sound
        # For now, just log the sound event
        self.logger.info(f"Alert sound: {level}")
    
    def export_alerts(self):
        """Export current alerts to file."""
        try:
            filename = f"temperature_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            # In a real implementation, this would open a file dialog
            messagebox.showinfo("Export", f"Alerts would be exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export alerts: {e}")
    
    def export_config(self):
        """Export alert configuration."""
        try:
            filename = f"alert_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            messagebox.showinfo("Export", f"Configuration would be exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export configuration: {e}")
    
    def update_sound_setting(self):
        """Update sound notification setting."""
        self.config['enable_sound'] = self.sound_var.get()
    
    def update_notifications_setting(self):
        """Update desktop notification setting."""
        self.config['enable_notifications'] = self.notifications_var.get()
    
    def update_timeout_setting(self):
        """Update auto-acknowledge timeout setting."""
        try:
            timeout = int(self.timeout_var.get())
            self.config['auto_acknowledge_timeout'] = timeout
        except ValueError:
            self.timeout_var.set(str(self.config['auto_acknowledge_timeout']))


if __name__ == "__main__":
    # Test the alert monitor
    root = tk.Tk()
    root.title("Temperature Alert Monitor Test")
    root.geometry("800x600")
    
    def alert_callback(action, data):
        print(f"Alert action: {action}, data: {data}")
    
    monitor = AlertMonitor(root, alert_callback)
    monitor.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Add some test alerts
    monitor.add_alert(AlertLevel.INFO, "System started", 22.5)
    monitor.add_alert(AlertLevel.WARNING, "Temperature rising", 68.2)
    monitor.add_alert(AlertLevel.CRITICAL, "Temperature exceeds limit", 82.1)
    
    root.mainloop()
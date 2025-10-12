"""
Temperature Dashboard Component

Real-time temperature visualization using Seaborn and matplotlib
for the Challenge 2025 temperature sensor GUI.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Set Seaborn style
sns.set_style("whitegrid")
sns.set_palette("husl")


class TemperatureDashboard:
    """Temperature dashboard with real-time Seaborn visualizations."""
    
    def __init__(self, parent):
        """Initialize the temperature dashboard."""
        self.parent = parent
        self.figure = None
        self.canvas = None
        self.ax_main = None
        self.ax_stats = None
        
        # Data for visualization
        self.temperature_history = []
        self.timestamp_history = []
        self.alert_history = []
        
        # Configuration
        self.max_points = 500  # Maximum points to display
        self.update_interval = 1.0  # seconds
        
        self.setup_dashboard()
    
    def setup_dashboard(self):
        """Setup the dashboard layout and plots."""
        # Create main frame
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create matplotlib figure with subplots
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.figure.suptitle('Challenge 2025 Temperature Sensor Dashboard', fontsize=14, fontweight='bold')
        
        # Main temperature plot (top 70%)
        self.ax_main = self.figure.add_subplot(2, 1, 1)
        
        # Statistics plot (bottom 30%)
        self.ax_stats = self.figure.add_subplot(2, 1, 2)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Dashboard controls
        self.setup_controls(control_frame)
        
        # Initialize empty plots
        self.initialize_plots()
    
    def setup_controls(self, parent):
        """Setup dashboard control widgets."""
        # Time range selection
        ttk.Label(parent, text="Time Range:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.time_range_var = tk.StringVar(value="5 minutes")
        time_range_combo = ttk.Combobox(parent, textvariable=self.time_range_var,
                                       values=["1 minute", "5 minutes", "15 minutes", "1 hour"],
                                       state="readonly", width=10)
        time_range_combo.pack(side=tk.LEFT, padx=(0, 10))
        time_range_combo.bind("<<ComboboxSelected>>", self.on_time_range_change)
        
        # Auto-scale toggle
        self.auto_scale_var = tk.BooleanVar(value=True)
        auto_scale_check = ttk.Checkbutton(parent, text="Auto Scale Y-axis",
                                          variable=self.auto_scale_var)
        auto_scale_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Show alerts toggle
        self.show_alerts_var = tk.BooleanVar(value=True)
        show_alerts_check = ttk.Checkbutton(parent, text="Show Alerts",
                                           variable=self.show_alerts_var)
        show_alerts_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear data button
        clear_button = ttk.Button(parent, text="Clear Data", command=self.clear_data)
        clear_button.pack(side=tk.RIGHT)
    
    def initialize_plots(self):
        """Initialize empty plots with proper styling."""
        # Main temperature plot
        self.ax_main.clear()
        self.ax_main.set_title('Real-time Temperature Monitoring', fontsize=12, fontweight='bold')
        self.ax_main.set_xlabel('Time')
        self.ax_main.set_ylabel('Temperature (°C)')
        self.ax_main.grid(True, alpha=0.3)
        
        # Add placeholder text
        self.ax_main.text(0.5, 0.5, 'Waiting for temperature data...', 
                         horizontalalignment='center', verticalalignment='center',
                         transform=self.ax_main.transAxes, fontsize=12, alpha=0.6)
        
        # Statistics plot
        self.ax_stats.clear()
        self.ax_stats.set_title('Temperature Statistics (Last 100 samples)', fontsize=10)
        
        # Draw initial plots
        self.canvas.draw()
    
    def update_temperature_plot(self, timestamps, temperatures, alerts=None):
        """
        Update the temperature plot with new data.
        
        Args:
            timestamps: List of datetime objects
            temperatures: List of temperature values in Celsius
            alerts: List of alert events (optional)
        """
        if not timestamps or not temperatures:
            return
        
        try:
            # Filter data based on time range
            filtered_data = self.filter_data_by_time_range(timestamps, temperatures, alerts)
            if not filtered_data:
                return
            
            filtered_timestamps, filtered_temps, filtered_alerts = filtered_data
            
            # Update main temperature plot
            self.update_main_plot(filtered_timestamps, filtered_temps, filtered_alerts)
            
            # Update statistics plot
            self.update_statistics_plot(temperatures[-100:])  # Last 100 samples
            
            # Refresh canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating temperature plot: {e}")
    
    def filter_data_by_time_range(self, timestamps, temperatures, alerts):
        """Filter data based on selected time range."""
        if not timestamps:
            return None
        
        # Parse time range
        time_range_str = self.time_range_var.get()
        if "minute" in time_range_str:
            minutes = int(time_range_str.split()[0])
            time_delta = timedelta(minutes=minutes)
        elif "hour" in time_range_str:
            hours = int(time_range_str.split()[0])
            time_delta = timedelta(hours=hours)
        else:
            time_delta = timedelta(minutes=5)  # Default
        
        # Filter based on time range
        cutoff_time = datetime.now() - time_delta
        
        filtered_timestamps = []
        filtered_temps = []
        
        for i, ts in enumerate(timestamps):
            if ts >= cutoff_time:
                filtered_timestamps.append(ts)
                filtered_temps.append(temperatures[i])
        
        # Filter alerts
        filtered_alerts = []
        if alerts and self.show_alerts_var.get():
            for alert in alerts:
                if alert['timestamp'] >= cutoff_time:
                    filtered_alerts.append(alert)
        
        return filtered_timestamps, filtered_temps, filtered_alerts
    
    def update_main_plot(self, timestamps, temperatures, alerts):
        """Update the main temperature plot."""
        self.ax_main.clear()
        
        if not timestamps or not temperatures:
            self.ax_main.text(0.5, 0.5, 'No data in selected time range', 
                             horizontalalignment='center', verticalalignment='center',
                             transform=self.ax_main.transAxes, fontsize=12, alpha=0.6)
            return
        
        # Convert to pandas DataFrame for Seaborn
        df = pd.DataFrame({
            'time': timestamps,
            'temperature': temperatures
        })
        
        # Create main temperature line plot
        sns.lineplot(data=df, x='time', y='temperature', ax=self.ax_main, 
                    linewidth=2, color='steelblue', label='Temperature')
        
        # Add moving average if enough data points
        if len(temperatures) > 10:
            window_size = min(10, len(temperatures) // 4)
            df['temp_smooth'] = df['temperature'].rolling(window=window_size, center=True).mean()
            sns.lineplot(data=df, x='time', y='temp_smooth', ax=self.ax_main,
                        linewidth=1, color='orange', alpha=0.7, label='Moving Average')
        
        # Add alert markers
        if alerts:
            alert_times = [alert['timestamp'] for alert in alerts]
            alert_temps = [alert['temperature'] for alert in alerts]
            
            self.ax_main.scatter(alert_times, alert_temps, 
                               color='red', s=100, marker='!', 
                               label='Alerts', zorder=5, alpha=0.8)
        
        # Styling
        self.ax_main.set_title('Real-time Temperature Monitoring', fontsize=12, fontweight='bold')
        self.ax_main.set_xlabel('Time')
        self.ax_main.set_ylabel('Temperature (°C)')
        self.ax_main.grid(True, alpha=0.3)
        self.ax_main.legend()
        
        # Auto-scale or fixed scale
        if self.auto_scale_var.get():
            self.ax_main.relim()
            self.ax_main.autoscale_view()
        
        # Format x-axis for time
        self.ax_main.tick_params(axis='x', rotation=45)
        
        # Add current temperature annotation
        if temperatures:
            current_temp = temperatures[-1]
            self.ax_main.annotate(f'Current: {current_temp:.1f}°C',
                                xy=(timestamps[-1], current_temp),
                                xytext=(10, 10), textcoords='offset points',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    def update_statistics_plot(self, recent_temperatures):
        """Update the statistics plot with distribution and metrics."""
        self.ax_stats.clear()
        
        if len(recent_temperatures) < 5:
            self.ax_stats.text(0.5, 0.5, 'Insufficient data for statistics', 
                             horizontalalignment='center', verticalalignment='center',
                             transform=self.ax_stats.transAxes, fontsize=10, alpha=0.6)
            return
        
        # Create DataFrame
        df = pd.DataFrame({'temperature': recent_temperatures})
        
        # Create histogram with KDE
        sns.histplot(data=df, x='temperature', kde=True, ax=self.ax_stats,
                    bins=min(20, len(recent_temperatures) // 3),
                    alpha=0.7, color='lightblue')
        
        # Add statistics text
        mean_temp = np.mean(recent_temperatures)
        std_temp = np.std(recent_temperatures)
        min_temp = np.min(recent_temperatures)
        max_temp = np.max(recent_temperatures)
        
        stats_text = (f'Mean: {mean_temp:.2f}°C\n'
                     f'Std: {std_temp:.2f}°C\n'
                     f'Range: {min_temp:.1f}°C - {max_temp:.1f}°C')
        
        self.ax_stats.text(0.02, 0.98, stats_text,
                          transform=self.ax_stats.transAxes,
                          verticalalignment='top',
                          bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Add mean line
        self.ax_stats.axvline(mean_temp, color='red', linestyle='--', 
                             alpha=0.7, label=f'Mean: {mean_temp:.2f}°C')
        
        # Styling
        self.ax_stats.set_title('Temperature Distribution (Last 100 samples)', fontsize=10)
        self.ax_stats.set_xlabel('Temperature (°C)')
        self.ax_stats.set_ylabel('Frequency')
        self.ax_stats.grid(True, alpha=0.3)
        self.ax_stats.legend()
    
    def on_time_range_change(self, event=None):
        """Handle time range selection change."""
        logger.debug(f"Time range changed to: {self.time_range_var.get()}")
        # The plot will be updated on the next data update
    
    def clear_data(self):
        """Clear all data and reset plots."""
        self.temperature_history.clear()
        self.timestamp_history.clear()
        self.alert_history.clear()
        
        self.initialize_plots()
        logger.info("Dashboard data cleared")
    
    def export_plot(self, filename):
        """Export current plot to file."""
        try:
            self.figure.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Plot exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export plot: {e}")
            raise
    
    def get_plot_summary(self):
        """Get summary of current plot data."""
        if not self.temperature_history:
            return "No data available"
        
        recent_temps = self.temperature_history[-100:]  # Last 100 samples
        
        summary = {
            'total_samples': len(self.temperature_history),
            'mean_temperature': np.mean(recent_temps),
            'std_temperature': np.std(recent_temps),
            'min_temperature': np.min(recent_temps),
            'max_temperature': np.max(recent_temps),
            'total_alerts': len(self.alert_history),
            'time_range': self.time_range_var.get()
        }
        
        return summary


if __name__ == "__main__":
    # Test the dashboard component
    import numpy as np
    from datetime import datetime, timedelta
    
    root = tk.Tk()
    root.title("Temperature Dashboard Test")
    
    dashboard = TemperatureDashboard(root)
    
    # Generate test data
    now = datetime.now()
    timestamps = [now - timedelta(minutes=i) for i in range(60, 0, -1)]
    temperatures = 25 + 5 * np.sin(np.linspace(0, 4*np.pi, 60)) + np.random.normal(0, 0.5, 60)
    
    # Add some alert events
    alerts = [
        {'timestamp': timestamps[20], 'temperature': temperatures[20], 'type': 'threshold_crossed'},
        {'timestamp': timestamps[40], 'temperature': temperatures[40], 'type': 'threshold_crossed'}
    ]
    
    # Update dashboard
    dashboard.update_temperature_plot(timestamps, temperatures, alerts)
    
    root.mainloop()
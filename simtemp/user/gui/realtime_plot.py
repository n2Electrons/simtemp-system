#!/usr/bin/env python3
"""
Real-time Temperature Plot Widget
Copyright (c) 2025 Jorge Rodriguez Moreno

Real-time temperature plotting widget with threshold line and alarm zones.
"""

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import threading
import time


class RealTimePlot(ctk.CTkFrame):
    """
    Real-time temperature plotting widget with threshold visualization.
    """
    
    def __init__(self, master, width=600, height=400, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        
        self.width = width
        self.height = height
        
        # Data storage
        self.max_points = 300  # 5 minutes at 1Hz
        self.timestamps = deque(maxlen=self.max_points)
        self.temperatures = deque(maxlen=self.max_points)
        self.threshold_temp = 45.0
        
        # Plot settings
        self.temp_range = (-10, 100)
        self.time_window = 300  # seconds (5 minutes)
        
        # Colors based on CustomTkinter theme
        self.setup_colors()
        
        # Create matplotlib figure
        self.setup_matplotlib()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        # Animation
        self.animation = None
        self.is_animating = False
        
        # Generate some initial data for testing
        self.generate_test_data()
    
    def setup_colors(self):
        """Setup colors based on CustomTkinter appearance mode."""
        if ctk.get_appearance_mode() == "Dark":
            self.bg_color = "#212121"
            self.plot_bg = "#2b2b2b"
            self.text_color = "#ffffff"
            self.grid_color = "#404040"
            self.temp_color = "#00d4ff"
            self.threshold_color = "#ff6b6b"
            self.alarm_zone_color = "#ff6b6b"
        else:
            self.bg_color = "#f0f0f0"
            self.plot_bg = "#ffffff"
            self.text_color = "#000000"
            self.grid_color = "#cccccc"
            self.temp_color = "#0066cc"
            self.threshold_color = "#cc0000"
            self.alarm_zone_color = "#ffcccc"
    
    def setup_matplotlib(self):
        """Setup matplotlib figure and axes."""
        # Set matplotlib style for dark theme
        plt.style.use('dark_background' if ctk.get_appearance_mode() == "Dark" 
                     else 'default')
        
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.fig.patch.set_facecolor(self.bg_color)
        self.ax.set_facecolor(self.plot_bg)
        
        # Configure axes
        self.ax.set_ylabel('Temperature (°C)', color=self.text_color, fontsize=12)
        self.ax.set_xlabel('Time', color=self.text_color, fontsize=12)
        self.ax.tick_params(colors=self.text_color)
        self.ax.grid(True, color=self.grid_color, alpha=0.3)
        
        # Set temperature range
        self.ax.set_ylim(self.temp_range)
        
        # Initialize empty line plots
        self.temp_line, = self.ax.plot([], [], color=self.temp_color, 
                                      linewidth=2, label='Temperature')
        self.threshold_line = self.ax.axhline(y=self.threshold_temp, 
                                            color=self.threshold_color,
                                            linestyle='--', linewidth=2, 
                                            label='Threshold')
        
        # Alarm zone (above threshold)
        self.alarm_zone = self.ax.axhspan(self.threshold_temp, self.temp_range[1],
                                         alpha=0.2, color=self.alarm_zone_color,
                                         label='Alarm Zone')
        
        # Legend
        self.ax.legend(loc='upper left', fontsize=10)
        
        # Tight layout
        self.fig.tight_layout()
    
    def add_data_point(self, temperature, timestamp=None):
        """Add a new temperature data point."""
        if timestamp is None:
            timestamp = datetime.now()
        elif isinstance(timestamp, (int, float)):
            # Convert Unix timestamp to datetime
            timestamp = datetime.fromtimestamp(timestamp)
        # If timestamp is already a datetime object, use it as-is
        
        self.timestamps.append(timestamp)
        self.temperatures.append(temperature)
        
        # Update plot if not animating
        if not self.is_animating:
            self.update_plot()
    
    def set_threshold(self, threshold):
        """Update threshold temperature."""
        self.threshold_temp = threshold
        
        # Update threshold line
        self.threshold_line.set_ydata([threshold, threshold])
        
        # Update alarm zone
        self.alarm_zone.remove()
        self.alarm_zone = self.ax.axhspan(threshold, self.temp_range[1],
                                         alpha=0.2, color=self.alarm_zone_color,
                                         label='Alarm Zone')
        
        self.canvas.draw()
    
    def update_plot(self):
        """Update the temperature plot."""
        if len(self.timestamps) == 0:
            return
        
        # Convert timestamps to relative time in seconds
        current_time = datetime.now()
        time_data = [(current_time - ts).total_seconds() 
                     for ts in self.timestamps]
        time_data = [-t for t in time_data]  # Make negative for past times
        
        # Update temperature line
        self.temp_line.set_data(time_data, list(self.temperatures))
        
        # Update x-axis limits to show last time_window seconds
        self.ax.set_xlim(-self.time_window, 0)
        
        # Update x-axis labels
        self.update_time_labels()
        
        # Redraw canvas
        self.canvas.draw()
    
    def update_time_labels(self):
        """Update time axis labels."""
        # Set x-axis to show time in MM:SS format
        current_time = datetime.now()
        
        # Create time ticks
        time_ticks = []
        time_labels = []
        
        for i in range(0, self.time_window + 1, 60):  # Every minute
            time_ticks.append(-i)
            past_time = current_time - timedelta(seconds=i)
            time_labels.append(past_time.strftime('%H:%M'))
        
        self.ax.set_xticks(time_ticks)
        self.ax.set_xticklabels(time_labels)
    
    def start_animation(self, interval=1000):
        """Start real-time animation."""
        if self.animation is not None:
            self.animation.event_source.stop()
        
        self.is_animating = True
        self.animation = FuncAnimation(
            self.fig, self._animate, interval=interval, blit=False)
        self.canvas.draw()
    
    def stop_animation(self):
        """Stop real-time animation."""
        if self.animation is not None:
            self.animation.event_source.stop()
            self.animation = None
        self.is_animating = False
    
    def _animate(self, frame):
        """Animation function called by FuncAnimation."""
        self.update_plot()
        return [self.temp_line]
    
    def clear_data(self):
        """Clear all temperature data."""
        self.timestamps.clear()
        self.temperatures.clear()
        self.update_plot()
    
    def get_current_stats(self):
        """Get current temperature statistics."""
        if len(self.temperatures) == 0:
            return None
        
        temps = list(self.temperatures)
        return {
            'current': temps[-1],
            'min': min(temps),
            'max': max(temps),
            'avg': sum(temps) / len(temps),
            'count': len(temps)
        }
    
    def generate_test_data(self):
        """Generate test data for demonstration."""
        # Generate 2 minutes of test data
        current_time = datetime.now()
        
        for i in range(120):  # 2 minutes of data
            timestamp = current_time - timedelta(seconds=120-i)
            # Generate sinusoidal temperature with some noise
            temp = 35 + 15 * np.sin(i * 0.1) + np.random.normal(0, 2)
            self.timestamps.append(timestamp)
            self.temperatures.append(temp)
    
    def set_time_window(self, seconds):
        """Set the time window for display."""
        self.time_window = seconds
        self.max_points = max(seconds, 300)  # At least 5 minutes of storage
        
        # Update deques with new max length
        new_timestamps = deque(self.timestamps, maxlen=self.max_points)
        new_temperatures = deque(self.temperatures, maxlen=self.max_points)
        self.timestamps = new_timestamps
        self.temperatures = new_temperatures
        
        self.update_plot()
    
    def export_data(self, filename):
        """Export temperature data to CSV file."""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'Temperature'])
            
            for timestamp, temp in zip(self.timestamps, self.temperatures):
                writer.writerow([timestamp.isoformat(), temp])


def test_realtime_plot():
    """Test the real-time plot widget."""
    root = ctk.CTk()
    root.title("Real-time Temperature Plot Test")
    root.geometry("800x600")
    
    ctk.set_appearance_mode("dark")
    
    # Create plot
    plot = RealTimePlot(root, width=750, height=500)
    plot.pack(padx=20, pady=20, fill="both", expand=True)
    
    # Control frame
    control_frame = ctk.CTkFrame(root)
    control_frame.pack(padx=20, pady=10, fill="x")
    
    # Start/Stop buttons
    start_btn = ctk.CTkButton(control_frame, text="Start Animation",
                             command=lambda: plot.start_animation(500))
    start_btn.pack(side="left", padx=5)
    
    stop_btn = ctk.CTkButton(control_frame, text="Stop Animation",
                            command=plot.stop_animation)
    stop_btn.pack(side="left", padx=5)
    
    clear_btn = ctk.CTkButton(control_frame, text="Clear Data",
                             command=plot.clear_data)
    clear_btn.pack(side="left", padx=5)
    
    # Threshold slider
    threshold_label = ctk.CTkLabel(control_frame, text="Threshold:")
    threshold_label.pack(side="left", padx=(20, 5))
    
    threshold_slider = ctk.CTkSlider(control_frame, from_=0, to=100, 
                                   number_of_steps=100)
    threshold_slider.set(45)
    threshold_slider.pack(side="left", padx=5)
    
    def update_threshold(value):
        plot.set_threshold(value)
    
    threshold_slider.configure(command=update_threshold)
    
    # Add data simulation
    def simulate_data():
        import random
        while True:
            temp = 40 + random.gauss(0, 5)  # Normal distribution around 40°C
            plot.add_data_point(temp)
            time.sleep(1)
    
    # Start data simulation in background
    data_thread = threading.Thread(target=simulate_data, daemon=True)
    data_thread.start()
    
    root.mainloop()


if __name__ == "__main__":
    test_realtime_plot()
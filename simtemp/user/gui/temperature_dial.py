#!/usr/bin/env python3
"""
Temperature Dial Widget
Copyright (c) 2025 Jorge Rodriguez Moreno

Circular temperature dial widget with threshold visualization and alarm indication.
"""

import customtkinter as ctk
import math
import tkinter as tk


class TemperatureDial(ctk.CTkFrame):
    """
    Circular temperature dial widget with threshold line and alarm indication.
    """
    
    def __init__(self, master, width=250, height=250, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        
        # Configuration
        self.width = width
        self.height = height
        self.radius = min(width, height) // 2 - 20
        self.center_x = width // 2
        self.center_y = height // 2
        
        # Temperature settings
        self.min_temp = -10
        self.max_temp = 100
        self.current_temp = 25.0
        self.threshold_temp = 45.0
        self.alarm_active = False
        
        # Colors
        self.dial_color = "#2b2b2b"
        self.needle_color = "#00d4ff"
        self.threshold_color = "#ff6b6b"
        self.alarm_color = "#ff0000"
        self.text_color = "#ffffff"
        self.scale_color = "#888888"
        
        # Create canvas
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=self._get_frame_color(),
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Draw initial dial
        self.draw_dial()
    
    def _get_frame_color(self):
        """Get frame background color based on appearance mode."""
        if ctk.get_appearance_mode() == "Dark":
            return "#212121"
        else:
            return "#f0f0f0"
    
    def set_temperature(self, temp):
        """Set current temperature value."""
        self.current_temp = max(self.min_temp, min(self.max_temp, temp))
        self.alarm_active = self.current_temp >= self.threshold_temp
        self.draw_dial()
    
    def set_threshold(self, threshold):
        """Set threshold temperature."""
        self.threshold_temp = threshold
        self.alarm_active = self.current_temp >= self.threshold_temp
        self.draw_dial()
    
    def draw_dial(self):
        """Draw the complete temperature dial."""
        self.canvas.delete("all")
        
        # Draw outer ring
        self.canvas.create_oval(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
            outline=self.scale_color,
            width=3,
            fill=""
        )
        
        # Draw temperature scale
        self.draw_temperature_scale()
        
        # Draw threshold line
        self.draw_threshold_line()
        
        # Draw temperature needle
        self.draw_needle()
        
        # Draw center dot
        self.canvas.create_oval(
            self.center_x - 8,
            self.center_y - 8,
            self.center_x + 8,
            self.center_y + 8,
            fill=self.needle_color,
            outline=""
        )
        
        # Draw temperature text
        temp_text = f"{self.current_temp:.1f}°C"
        text_color = self.alarm_color if self.alarm_active else self.text_color
        self.canvas.create_text(
            self.center_x,
            self.center_y + 40,
            text=temp_text,
            fill=text_color,
            font=("Arial", 16, "bold")
        )
        
        # Draw alarm indicator
        if self.alarm_active:
            self.draw_alarm_indicator()
    
    def draw_temperature_scale(self):
        """Draw temperature scale markings."""
        # Major ticks every 10 degrees
        for temp in range(self.min_temp, self.max_temp + 1, 10):
            angle = self.temp_to_angle(temp)
            x1, y1 = self.polar_to_cartesian(angle, self.radius - 15)
            x2, y2 = self.polar_to_cartesian(angle, self.radius - 5)
            
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill=self.scale_color,
                width=2
            )
            
            # Temperature labels
            if temp % 20 == 0:  # Label every 20 degrees
                label_x, label_y = self.polar_to_cartesian(angle, self.radius - 30)
                self.canvas.create_text(
                    label_x, label_y,
                    text=str(temp),
                    fill=self.scale_color,
                    font=("Arial", 10)
                )
        
        # Minor ticks every 5 degrees
        for temp in range(self.min_temp, self.max_temp + 1, 5):
            if temp % 10 != 0:  # Don't draw over major ticks
                angle = self.temp_to_angle(temp)
                x1, y1 = self.polar_to_cartesian(angle, self.radius - 10)
                x2, y2 = self.polar_to_cartesian(angle, self.radius - 5)
                
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=self.scale_color,
                    width=1
                )
    
    def draw_threshold_line(self):
        """Draw threshold temperature line."""
        angle = self.temp_to_angle(self.threshold_temp)
        x1, y1 = self.polar_to_cartesian(angle, 20)
        x2, y2 = self.polar_to_cartesian(angle, self.radius - 5)
        
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=self.threshold_color,
            width=3
        )
        
        # Threshold label
        label_x, label_y = self.polar_to_cartesian(angle, self.radius + 15)
        self.canvas.create_text(
            label_x, label_y,
            text=f"T: {self.threshold_temp:.0f}°C",
            fill=self.threshold_color,
            font=("Arial", 9, "bold")
        )
    
    def draw_needle(self):
        """Draw temperature needle."""
        angle = self.temp_to_angle(self.current_temp)
        
        # Needle line
        x1, y1 = self.polar_to_cartesian(angle, 15)
        x2, y2 = self.polar_to_cartesian(angle, self.radius - 25)
        
        needle_color = self.alarm_color if self.alarm_active else self.needle_color
        
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=needle_color,
            width=4
        )
        
        # Needle tip
        tip_x, tip_y = self.polar_to_cartesian(angle, self.radius - 20)
        self.canvas.create_oval(
            tip_x - 3, tip_y - 3,
            tip_x + 3, tip_y + 3,
            fill=needle_color,
            outline=""
        )
    
    def draw_alarm_indicator(self):
        """Draw alarm indicator (red circle)."""
        alarm_radius = 12
        self.canvas.create_oval(
            self.center_x - alarm_radius,
            self.center_y - self.radius + 30 - alarm_radius,
            self.center_x + alarm_radius,
            self.center_y - self.radius + 30 + alarm_radius,
            fill=self.alarm_color,
            outline=""
        )
        
        # Alarm text
        self.canvas.create_text(
            self.center_x,
            self.center_y - self.radius + 30,
            text="!",
            fill="white",
            font=("Arial", 14, "bold")
        )
        
        # ALARM text
        self.canvas.create_text(
            self.center_x,
            self.center_y - self.radius + 50,
            text="ALARM",
            fill=self.alarm_color,
            font=("Arial", 10, "bold")
        )
    
    def temp_to_angle(self, temp):
        """Convert temperature to angle in degrees."""
        # Map temperature range to 270 degrees (from -135 to +135 degrees)
        temp_range = self.max_temp - self.min_temp
        angle_range = 270
        
        normalized_temp = (temp - self.min_temp) / temp_range
        angle = -135 + (normalized_temp * angle_range)
        
        return math.radians(angle)
    
    def polar_to_cartesian(self, angle, radius):
        """Convert polar coordinates to cartesian."""
        x = self.center_x + radius * math.cos(angle)
        y = self.center_y + radius * math.sin(angle)
        return x, y


def test_dial():
    """Test the temperature dial widget."""
    root = ctk.CTk()
    root.title("Temperature Dial Test")
    root.geometry("400x400")
    
    ctk.set_appearance_mode("dark")
    
    dial = TemperatureDial(root, width=300, height=300)
    dial.pack(padx=20, pady=20)
    
    # Test with different temperatures
    import time
    import threading
    
    def update_temp():
        temps = [20, 30, 40, 50, 60, 45, 25]
        for temp in temps:
            dial.set_temperature(temp)
            root.update()
            time.sleep(1)
    
    # Start test after a delay
    threading.Timer(1.0, update_temp).start()
    
    root.mainloop()


if __name__ == "__main__":
    test_dial()
#!/usr/bin/env python3
"""
7-Segment Display Widget
Copyright (c) 2025 Jorge Rodriguez Moreno

Digital 7-segment display widget for showing temperature values.
"""

import customtkinter as ctk
import tkinter as tk


class SevenSegmentDisplay(ctk.CTkFrame):
    """
    7-segment display widget for showing numerical temperature values.
    """
    
    def __init__(self, master, digits=4, width=300, height=100, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        
        self.digits = digits
        self.width = width
        self.height = height
        self.digit_width = (width - 20) // digits
        self.digit_height = height - 20
        
        # Display value
        self.value = "00.0"
        self.decimal_places = 1
        
        # Colors
        self.on_color = "#00ff00"    # Green for active segments
        self.off_color = "#1a1a1a"   # Dark gray for inactive segments
        self.bg_color = "#000000"    # Black background
        self.alarm_color = "#ff0000" # Red for alarm state
        
        # Alarm state
        self.alarm_state = False
        
        # Create canvas
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=self.bg_color,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 7-segment patterns for digits 0-9
        self.digit_patterns = {
            '0': [1, 1, 1, 1, 1, 1, 0],  # a,b,c,d,e,f,g
            '1': [0, 1, 1, 0, 0, 0, 0],
            '2': [1, 1, 0, 1, 1, 0, 1],
            '3': [1, 1, 1, 1, 0, 0, 1],
            '4': [0, 1, 1, 0, 0, 1, 1],
            '5': [1, 0, 1, 1, 0, 1, 1],
            '6': [1, 0, 1, 1, 1, 1, 1],
            '7': [1, 1, 1, 0, 0, 0, 0],
            '8': [1, 1, 1, 1, 1, 1, 1],
            '9': [1, 1, 1, 1, 0, 1, 1],
            '.': [0, 0, 0, 0, 0, 0, 0],  # Special case for decimal point
            '-': [0, 0, 0, 0, 0, 0, 1],  # Minus sign (center segment)
            ' ': [0, 0, 0, 0, 0, 0, 0],  # Blank
        }
        
        # Draw initial display
        self.draw_display()
    
    def set_value(self, value, alarm=False):
        """Set the display value."""
        self.alarm_state = alarm
        
        if isinstance(value, (int, float)):
            # Format as temperature with 1 decimal place
            self.value = f"{value:4.1f}"
        else:
            self.value = str(value)
        
        # Ensure value fits in available digits
        if len(self.value.replace('.', '')) > self.digits:
            self.value = "ERR"
        
        self.draw_display()
    
    def draw_display(self):
        """Draw the complete 7-segment display."""
        self.canvas.delete("all")
        
        # Calculate starting position
        total_width = len(self.value) * self.digit_width
        start_x = (self.width - total_width) // 2
        
        # Draw each character
        for i, char in enumerate(self.value):
            x_pos = start_x + i * self.digit_width
            
            if char == '.':
                self.draw_decimal_point(x_pos, 10)
            else:
                self.draw_digit(char, x_pos, 10)
    
    def draw_digit(self, digit, x, y):
        """Draw a single 7-segment digit."""
        if digit not in self.digit_patterns:
            digit = ' '  # Default to blank for unknown characters
        
        pattern = self.digit_patterns[digit]
        
        # Segment coordinates relative to digit position
        seg_width = self.digit_width - 20
        seg_height = self.digit_height - 20
        thickness = 6
        
        # Define segment positions
        segments = {
            'a': [(x + 10, y), (x + seg_width, y), thickness, 'horizontal'],
            'b': [(x + seg_width, y), (x + seg_width, y + seg_height//2), 
                  thickness, 'vertical'],
            'c': [(x + seg_width, y + seg_height//2), 
                  (x + seg_width, y + seg_height), thickness, 'vertical'],
            'd': [(x + seg_width, y + seg_height), (x + 10, y + seg_height), 
                  thickness, 'horizontal'],
            'e': [(x + 10, y + seg_height//2), (x + 10, y + seg_height), 
                  thickness, 'vertical'],
            'f': [(x + 10, y), (x + 10, y + seg_height//2), thickness, 'vertical'],
            'g': [(x + 10, y + seg_height//2), (x + seg_width, y + seg_height//2), 
                  thickness, 'horizontal']
        }
        
        # Draw segments
        segment_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        for i, seg_name in enumerate(segment_names):
            if i < len(pattern):
                is_on = pattern[i]
                seg_data = segments[seg_name]
                
                color = self.get_segment_color(is_on)
                self.draw_segment(seg_data[0], seg_data[1], seg_data[2], 
                                seg_data[3], color)
    
    def draw_segment(self, start, end, thickness, orientation, color):
        """Draw a single segment of the 7-segment display."""
        x1, y1 = start
        x2, y2 = end
        
        if orientation == 'horizontal':
            # Horizontal segment (trapezoid shape)
            points = [
                x1 + thickness//2, y1,
                x2 - thickness//2, y2,
                x2 - thickness//2, y2 + thickness,
                x1 + thickness//2, y1 + thickness
            ]
        else:  # vertical
            # Vertical segment (trapezoid shape)
            points = [
                x1, y1 + thickness//2,
                x1 + thickness, y1 + thickness//2,
                x2 + thickness, y2 - thickness//2,
                x2, y2 - thickness//2
            ]
        
        self.canvas.create_polygon(points, fill=color, outline="")
    
    def draw_decimal_point(self, x, y):
        """Draw a decimal point."""
        point_size = 8
        point_x = x + self.digit_width // 2
        point_y = y + self.digit_height - point_size
        
        color = self.get_segment_color(True)
        
        self.canvas.create_oval(
            point_x - point_size//2,
            point_y - point_size//2,
            point_x + point_size//2,
            point_y + point_size//2,
            fill=color,
            outline=""
        )
    
    def get_segment_color(self, is_on):
        """Get segment color based on state."""
        if not is_on:
            return self.off_color
        
        if self.alarm_state:
            return self.alarm_color
        else:
            return self.on_color
    
    def set_alarm_state(self, alarm):
        """Set alarm state (changes color to red)."""
        self.alarm_state = alarm
        self.draw_display()
    
    def flash_alarm(self, times=3, interval=500):
        """Flash the display for alarm indication."""
        def toggle_alarm():
            self.alarm_state = not self.alarm_state
            self.draw_display()
        
        # Flash sequence
        for i in range(times * 2):
            self.master.after(i * interval, toggle_alarm)


def test_seven_segment():
    """Test the 7-segment display widget."""
    root = ctk.CTk()
    root.title("7-Segment Display Test")
    root.geometry("500x300")
    
    ctk.set_appearance_mode("dark")
    
    # Create display
    display = SevenSegmentDisplay(root, digits=5, width=400, height=80)
    display.pack(padx=20, pady=20)
    
    # Test different values
    import time
    import threading
    
    def test_sequence():
        values = [25.5, 42.8, 99.9, -10.5, 100.0]
        alarms = [False, False, True, False, True]
        
        for value, alarm in zip(values, alarms):
            display.set_value(value, alarm)
            root.update()
            time.sleep(2)
        
        # Test flashing alarm
        display.set_value(75.0, True)
        display.flash_alarm(3, 300)
    
    # Start test after a delay
    threading.Timer(1.0, test_sequence).start()
    
    root.mainloop()


if __name__ == "__main__":
    test_seven_segment()
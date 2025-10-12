#!/usr/bin/env python3
"""
Control panel widget for temperature sensor configuration.
Provides UI controls for sampling rate, threshold settings, and device configuration.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
from typing import Callable, Optional, Dict, Any


class ControlPanel(ttk.Frame):
    """Control panel for temperature sensor configuration and control."""
    
    def __init__(self, parent, config_callback: Optional[Callable] = None):
        """
        Initialize the control panel.
        
        Args:
            parent: Parent widget
            config_callback: Callback function for configuration changes
        """
        super().__init__(parent)
        self.config_callback = config_callback
        self.logger = logging.getLogger(__name__)
        
        # Configuration state
        self.current_config = {
            'sampling_rate': 1000,  # ms
            'high_threshold': 75.0,  # °C
            'low_threshold': 10.0,   # °C
            'enable_alerts': True,
            'auto_sampling': True,
            'device_enabled': True
        }
        
        self.setup_ui()
        self.setup_validation()
    
    def setup_ui(self):
        """Set up the control panel user interface."""
        # Main frame with padding
        main_frame = ttk.LabelFrame(self, text="Temperature Sensor Control", padding="10")
        main_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Sampling Configuration
        sampling_frame = ttk.LabelFrame(main_frame, text="Sampling Configuration", padding="5")
        sampling_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Sampling rate control
        ttk.Label(sampling_frame, text="Sampling Rate (ms):").grid(row=0, column=0, sticky="w")
        self.sampling_var = tk.StringVar(value=str(self.current_config['sampling_rate']))
        sampling_spinbox = ttk.Spinbox(
            sampling_frame, 
            from_=100, 
            to=10000, 
            increment=100,
            textvariable=self.sampling_var,
            width=10,
            command=self.on_sampling_changed
        )
        sampling_spinbox.grid(row=0, column=1, sticky="w", padx=(5, 0))
        sampling_spinbox.bind('<KeyRelease>', self.on_sampling_changed)
        
        # Auto sampling checkbox
        self.auto_sampling_var = tk.BooleanVar(value=self.current_config['auto_sampling'])
        auto_check = ttk.Checkbutton(
            sampling_frame,
            text="Auto Sampling",
            variable=self.auto_sampling_var,
            command=self.on_auto_sampling_changed
        )
        auto_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        # Threshold Configuration
        threshold_frame = ttk.LabelFrame(main_frame, text="Temperature Thresholds", padding="5")
        threshold_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # High threshold
        ttk.Label(threshold_frame, text="High Threshold (°C):").grid(row=0, column=0, sticky="w")
        self.high_threshold_var = tk.StringVar(value=str(self.current_config['high_threshold']))
        high_spinbox = ttk.Spinbox(
            threshold_frame,
            from_=-50.0,
            to=150.0,
            increment=0.5,
            textvariable=self.high_threshold_var,
            width=10,
            command=self.on_threshold_changed
        )
        high_spinbox.grid(row=0, column=1, sticky="w", padx=(5, 0))
        high_spinbox.bind('<KeyRelease>', self.on_threshold_changed)
        
        # Low threshold
        ttk.Label(threshold_frame, text="Low Threshold (°C):").grid(row=1, column=0, sticky="w")
        self.low_threshold_var = tk.StringVar(value=str(self.current_config['low_threshold']))
        low_spinbox = ttk.Spinbox(
            threshold_frame,
            from_=-50.0,
            to=150.0,
            increment=0.5,
            textvariable=self.low_threshold_var,
            width=10,
            command=self.on_threshold_changed
        )
        low_spinbox.grid(row=1, column=1, sticky="w", padx=(5, 0))
        low_spinbox.bind('<KeyRelease>', self.on_threshold_changed)
        
        # Alert Configuration
        alert_frame = ttk.LabelFrame(main_frame, text="Alert Settings", padding="5")
        alert_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Enable alerts checkbox
        self.alerts_var = tk.BooleanVar(value=self.current_config['enable_alerts'])
        alerts_check = ttk.Checkbutton(
            alert_frame,
            text="Enable Temperature Alerts",
            variable=self.alerts_var,
            command=self.on_alerts_changed
        )
        alerts_check.grid(row=0, column=0, sticky="w")
        
        # Device Control
        device_frame = ttk.LabelFrame(main_frame, text="Device Control", padding="5")
        device_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Device enable/disable
        self.device_var = tk.BooleanVar(value=self.current_config['device_enabled'])
        device_check = ttk.Checkbutton(
            device_frame,
            text="Device Enabled",
            variable=self.device_var,
            command=self.on_device_changed
        )
        device_check.grid(row=0, column=0, sticky="w")
        
        # Control buttons
        button_frame = ttk.Frame(device_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.apply_button = ttk.Button(
            button_frame,
            text="Apply Settings",
            command=self.apply_configuration,
            style="Accent.TButton"
        )
        self.apply_button.pack(side="left", padx=(0, 5))
        
        self.reset_button = ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self.reset_configuration
        )
        self.reset_button.pack(side="left", padx=(0, 5))
        
        self.test_button = ttk.Button(
            button_frame,
            text="Test Configuration",
            command=self.test_configuration
        )
        self.test_button.pack(side="left")
        
        # Status display
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(anchor="w")
        
        # Configure column weights
        main_frame.columnconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
    
    def setup_validation(self):
        """Set up input validation for the form fields."""
        # Register validation commands
        vcmd = (self.register(self.validate_number), '%P')
        
        # Apply validation to numeric inputs
        for widget in self.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Spinbox):
                                grandchild.configure(validate='key', validatecommand=vcmd)
    
    def validate_number(self, value: str) -> bool:
        """
        Validate numeric input.
        
        Args:
            value: Input value to validate
            
        Returns:
            True if valid, False otherwise
        """
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def on_sampling_changed(self, event=None):
        """Handle sampling rate changes."""
        try:
            rate = int(self.sampling_var.get())
            if 100 <= rate <= 10000:
                self.current_config['sampling_rate'] = rate
                self.status_var.set(f"Sampling rate set to {rate}ms")
                self.logger.info(f"Sampling rate changed to {rate}ms")
            else:
                self.status_var.set("Invalid sampling rate (100-10000ms)")
        except ValueError:
            self.status_var.set("Invalid sampling rate value")
    
    def on_threshold_changed(self, event=None):
        """Handle threshold changes."""
        try:
            high_temp = float(self.high_threshold_var.get())
            low_temp = float(self.low_threshold_var.get())
            
            if low_temp >= high_temp:
                self.status_var.set("Low threshold must be less than high threshold")
                return
            
            self.current_config['high_threshold'] = high_temp
            self.current_config['low_threshold'] = low_temp
            self.status_var.set(f"Thresholds: {low_temp}°C - {high_temp}°C")
            self.logger.info(f"Thresholds changed: {low_temp}°C - {high_temp}°C")
            
        except ValueError:
            self.status_var.set("Invalid threshold values")
    
    def on_auto_sampling_changed(self):
        """Handle auto sampling toggle."""
        enabled = self.auto_sampling_var.get()
        self.current_config['auto_sampling'] = enabled
        status = "enabled" if enabled else "disabled"
        self.status_var.set(f"Auto sampling {status}")
        self.logger.info(f"Auto sampling {status}")
    
    def on_alerts_changed(self):
        """Handle alerts toggle."""
        enabled = self.alerts_var.get()
        self.current_config['enable_alerts'] = enabled
        status = "enabled" if enabled else "disabled"
        self.status_var.set(f"Alerts {status}")
        self.logger.info(f"Alerts {status}")
    
    def on_device_changed(self):
        """Handle device enable/disable."""
        enabled = self.device_var.get()
        self.current_config['device_enabled'] = enabled
        status = "enabled" if enabled else "disabled"
        self.status_var.set(f"Device {status}")
        self.logger.info(f"Device {status}")
    
    def apply_configuration(self):
        """Apply the current configuration."""
        try:
            if self.config_callback:
                self.config_callback(self.current_config.copy())
            
            self.status_var.set("Configuration applied successfully")
            self.logger.info("Configuration applied")
            
            # Temporarily disable the apply button
            self.apply_button.configure(state="disabled")
            self.after(2000, lambda: self.apply_button.configure(state="normal"))
            
        except Exception as e:
            error_msg = f"Failed to apply configuration: {str(e)}"
            self.status_var.set(error_msg)
            self.logger.error(error_msg)
            messagebox.showerror("Configuration Error", error_msg)
    
    def reset_configuration(self):
        """Reset configuration to defaults."""
        defaults = {
            'sampling_rate': 1000,
            'high_threshold': 75.0,
            'low_threshold': 10.0,
            'enable_alerts': True,
            'auto_sampling': True,
            'device_enabled': True
        }
        
        # Update UI
        self.sampling_var.set(str(defaults['sampling_rate']))
        self.high_threshold_var.set(str(defaults['high_threshold']))
        self.low_threshold_var.set(str(defaults['low_threshold']))
        self.auto_sampling_var.set(defaults['auto_sampling'])
        self.alerts_var.set(defaults['enable_alerts'])
        self.device_var.set(defaults['device_enabled'])
        
        # Update configuration
        self.current_config = defaults.copy()
        self.status_var.set("Configuration reset to defaults")
        self.logger.info("Configuration reset to defaults")
    
    def test_configuration(self):
        """Test the current configuration."""
        def test_thread():
            try:
                self.status_var.set("Testing configuration...")
                self.test_button.configure(state="disabled")
                
                # Simulate configuration test
                time.sleep(2)
                
                # Validate configuration
                errors = []
                if self.current_config['sampling_rate'] < 100:
                    errors.append("Sampling rate too low")
                if self.current_config['high_threshold'] <= self.current_config['low_threshold']:
                    errors.append("Invalid threshold range")
                
                if errors:
                    error_msg = "; ".join(errors)
                    self.status_var.set(f"Test failed: {error_msg}")
                    messagebox.showerror("Configuration Test Failed", error_msg)
                else:
                    self.status_var.set("Configuration test passed")
                    messagebox.showinfo("Configuration Test", "Configuration is valid and ready to use")
                
            except Exception as e:
                error_msg = f"Test error: {str(e)}"
                self.status_var.set(error_msg)
                self.logger.error(error_msg)
            finally:
                self.test_button.configure(state="normal")
        
        # Run test in background thread
        threading.Thread(target=test_thread, daemon=True).start()
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Current configuration dictionary
        """
        return self.current_config.copy()
    
    def set_configuration(self, config: Dict[str, Any]):
        """
        Set the configuration from external source.
        
        Args:
            config: Configuration dictionary to apply
        """
        try:
            # Update internal state
            self.current_config.update(config)
            
            # Update UI
            if 'sampling_rate' in config:
                self.sampling_var.set(str(config['sampling_rate']))
            if 'high_threshold' in config:
                self.high_threshold_var.set(str(config['high_threshold']))
            if 'low_threshold' in config:
                self.low_threshold_var.set(str(config['low_threshold']))
            if 'auto_sampling' in config:
                self.auto_sampling_var.set(config['auto_sampling'])
            if 'enable_alerts' in config:
                self.alerts_var.set(config['enable_alerts'])
            if 'device_enabled' in config:
                self.device_var.set(config['device_enabled'])
            
            self.status_var.set("Configuration updated")
            
        except Exception as e:
            error_msg = f"Failed to set configuration: {str(e)}"
            self.status_var.set(error_msg)
            self.logger.error(error_msg)


if __name__ == "__main__":
    # Test the control panel
    root = tk.Tk()
    root.title("Temperature Control Panel Test")
    root.geometry("400x600")
    
    def config_callback(config):
        print(f"Configuration changed: {config}")
    
    panel = ControlPanel(root, config_callback)
    panel.pack(fill="both", expand=True, padx=10, pady=10)
    
    root.mainloop()
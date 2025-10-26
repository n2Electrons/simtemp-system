#!/bin/bash
#
# SimTemp External GUI Launcher
# Copyright (c) 2025 Jorge Rodriguez Moreno
#
# Launcher script for the SimTemp External GUI application.
# This script activates the virtual environment and starts the GUI.
#

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/simtemp_gui_env"

echo "========================================================"
echo "SimTemp External GUI Launcher"
echo "Challenge 2025 - Temperature Sensor Monitor"
echo "========================================================"
echo

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at: $VENV_DIR"
    echo "Creating virtual environment..."
    
    cd "$SCRIPT_DIR"
    python3 -m venv simtemp_gui_env
    
    if [ $? -ne 0 ]; then
        echo " Failed to create virtual environment"
        exit 1
    fi
    
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo " Activating virtual environment..."
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo " Failed to activate virtual environment"
    exit 1
fi

echo "✓ Virtual environment activated"

# Check if dependencies are installed
echo " Checking dependencies..."
python3 -c "import customtkinter, matplotlib" 2>/dev/null

if [ $? -ne 0 ]; then
    echo " Installing dependencies..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
    
    if [  -ne 0 ]; then
        echo " Failed to install dependencies"
        exit 1
    fi
    
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi

# Launch GUI application
echo
echo " Starting SimTemp External GUI..."
echo "   Close the GUI window or press Ctrl+C to exit"
echo

cd "$SCRIPT_DIR"
python3 main.py

echo
echo " SimTemp External GUI closed"
#!/bin/bash
# AppLocker Deployment Script for Unix-like systems
# This script builds the AppLocker application into a standalone executable

echo "================================"
echo "AppLocker Deployment Script"
echo "================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed or not in PATH"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo "Installing PyInstaller..."
pip3 install pyinstaller
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install PyInstaller"
    exit 1
fi

echo "Running tests..."
python3 test_applocker.py
if [ $? -ne 0 ]; then
    echo "ERROR: Tests failed"
    exit 1
fi

echo "Building executable..."
pyinstaller --onefile --windowed --name AppLocker main.py
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build executable"
    exit 1
fi

echo "================================"
echo "Build completed successfully!"
echo "Executable location: dist/AppLocker"
echo "================================"

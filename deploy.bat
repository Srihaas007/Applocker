@echo off
REM AppLocker Deployment Script
REM This script builds the AppLocker application into a standalone executable

echo ================================
echo AppLocker Deployment Script
echo ================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo Running tests...
python test_applocker.py
if errorlevel 1 (
    echo ERROR: Tests failed
    pause
    exit /b 1
)

echo Building executable...
pyinstaller --onefile --windowed --name AppLocker --icon=assets/icon.ico main.py
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)

echo ================================
echo Build completed successfully!
echo Executable location: dist/AppLocker.exe
echo ================================

pause

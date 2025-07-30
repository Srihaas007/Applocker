"""
AppLocker Configuration Module

This module contains configuration settings for the AppLocker application.
"""

import os
from pathlib import Path

# Application Information
APP_NAME = "AppLocker"
APP_VERSION = "1.0.0"
APP_AUTHOR = "AppLocker Team"

# File Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# Data Files
USER_DATA_FILE = DATA_DIR / "user_data.txt"
LOCKED_APPS_FILE = DATA_DIR / "locked_apps.json"
QR_CODE_FILE = ASSETS_DIR / "qr_code.png"
LOG_FILE = LOGS_DIR / "app_logs.log"

# Security Settings
MIN_PIN_LENGTH = 4
MAX_PIN_LENGTH = 12
TOTP_WINDOW = 1  # Time window for TOTP validation (30 second intervals)

# GUI Settings
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"
WINDOW_GEOMETRY = "600x500"
QR_CODE_SIZE = (250, 250)

# Registry Paths for Windows Apps
UNINSTALL_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
UWP_APPS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft"

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
LOG_LEVEL = "INFO"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

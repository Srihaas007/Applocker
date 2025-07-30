# AppLocker - Installation Guide

## System Requirements

- Windows 10/11 (64-bit)
- Python 3.8+ (for development)
- 50MB free disk space
- Internet connection (for initial setup)

## Installation Options

### Option 1: Standalone Executable (Recommended for end users)

1. Download the latest `AppLocker.exe` from the releases page
2. Run the executable
3. Follow the setup wizard
4. Scan the QR code with Google Authenticator

### Option 2: From Source (For developers)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AppLocker.git
   cd AppLocker
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Building from Source

To build your own executable:

1. Install build dependencies:
   ```bash
   pip install pyinstaller
   ```

2. Run the deployment script:
   ```bash
   # Windows
   deploy.bat
   
   # Linux/Mac
   ./deploy.sh
   ```

## First Time Setup

1. **Master PIN**: Choose a secure 4-12 digit PIN
2. **2FA Setup**: Scan the QR code with Google Authenticator
3. **App Selection**: Choose which applications to lock

## Usage

### Locking Applications
1. Launch AppLocker
2. Click "Lock New Apps"
3. Select applications from the list
4. Enter your master PIN for each app

### Unlocking Applications
1. Select a locked app from the main interface
2. Click "Unlock Selected"
3. Enter your PIN
4. Enter the 2FA code from Google Authenticator

### Managing Locks
- **Remove Lock**: Select an app and click "Remove Lock"
- **View All**: See all currently locked applications
- **Add More**: Lock additional applications

## Security Features

- **PIN Protection**: bcrypt-hashed PINs
- **Two-Factor Authentication**: Time-based OTP
- **Secure Storage**: Encrypted credential storage
- **Audit Logging**: Complete activity logs

## Troubleshooting

### Common Issues

**Q: "User data not found" error**
A: Run the setup process again by deleting the `data/user_data.txt` file

**Q: Google Authenticator codes not working**
A: Ensure your system clock is accurate and try again

**Q: App not appearing in the list**
A: Some system apps may not be visible due to Windows permissions

**Q: Executable won't run**
A: Ensure you have the Visual C++ Redistributable installed

### Support

For additional support:
- Check the [Issues](https://github.com/yourusername/AppLocker/issues) page
- Create a new issue with detailed information
- Include log files from the `logs/` directory

## Uninstallation

1. Remove locks from all applications
2. Delete the AppLocker folder/executable
3. Remove the Google Authenticator entry (optional)

## Data Locations

- **User Data**: `data/user_data.txt`
- **Locked Apps**: `data/locked_apps.json`
- **Logs**: `logs/app_logs.log`
- **QR Codes**: `assets/qr_code.png`

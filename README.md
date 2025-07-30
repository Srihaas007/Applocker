# AppLocker

A secure Windows application that allows you to lock installed applications with PIN and 2FA authentication using Google Authenticator.

## Features

- 🔒 Lock any installed Windows application
- 📱 Two-factor authentication (2FA) with Google Authenticator
- 🔐 Secure PIN-based authentication with bcrypt hashing
- 📊 Comprehensive logging system
- 🖥️ User-friendly GUI interface
- 📋 App management (lock/unlock/remove locks)

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows operating system

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd AppLocker
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## First Time Setup

1. When you run the application for the first time, you'll be prompted to:
   - Set up a master PIN
   - Scan the QR code with Google Authenticator app

2. After setup, you can:
   - Browse installed applications
   - Select apps to lock with your PIN
   - Manage locked applications

## Usage

### Locking an Application

1. Run the application
2. Select "Lock New Apps" from the main interface
3. Choose an application from the list
4. Enter your PIN to lock the selected app

### Unlocking an Application

1. Select the locked app from the main interface
2. Click "Unlock Selected"
3. Enter your PIN
4. Enter the 2FA code from Google Authenticator

### Managing Locked Apps

- **View Locked Apps**: See all currently locked applications
- **Remove Lock**: Remove the lock from an application
- **Add New Locks**: Lock additional applications

## Security Features

- **PIN Hashing**: All PINs are securely hashed using bcrypt
- **2FA**: Additional security layer with time-based OTP
- **Secure Storage**: Encrypted storage of user credentials
- **Logging**: Comprehensive audit trail of all actions

## File Structure

```
AppLocker/
├── main.py              # Main entry point
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .gitignore          # Git ignore rules
├── user_data.txt       # User credentials (created after setup)
├── locked_apps.json    # Locked apps database (created after use)
├── app/
│   ├── __init__.py
│   ├── gui.py          # GUI interface
│   ├── auth.py         # Authentication logic
│   ├── app_lock.py     # App discovery and management
│   ├── user_data.py    # User data handling
│   └── logging.py      # Logging system
├── assets/
│   └── qr_code.png     # Generated QR code for 2FA setup
└── logs/
    └── app_logs.log    # Application logs
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Building Executable

```bash
pyinstaller main.spec
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security Considerations

- Always use strong PINs
- Keep your Google Authenticator app secure
- Don't share your QR code or secret key
- Regularly update the application

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue on GitHub or contact the development team.

## Changelog

### v1.0.0
- Initial release
- Basic app locking functionality
- 2FA integration
- GUI interface
- Logging system

# AppLocker

A secure Windows application that **actually blocks** installed applications using Google Authenticator 2FA authentication. No PINs required!

## 🚀 What's New (Latest Update)

- ✅ **NO MORE PINS** - Only Google Authenticator required
- ✅ **REAL APP BLOCKING** - Apps are actually prevented from running
- ✅ **IMPROVED UI** - Better app discovery with search and sorting
- ✅ **AUTOMATIC UNLOCKING** - Apps unlock for 1 hour after authentication
- ✅ **REAL-TIME MONITORING** - Background service monitors and blocks apps

## 🎯 Features

- 🔒 **Block ANY Windows application** - Really prevents apps from starting
- 📱 **Google Authenticator 2FA** - Secure authentication without PINs
- �️ **Improved User Interface** - Clean, modern, easy-to-use
- ⏰ **Temporary Unlocking** - Apps stay unlocked for 1 hour after auth
- � **Real-time Monitoring** - Background service actively blocks locked apps
- 📋 **Smart App Discovery** - Find apps easily with search and filtering
- 🔐 **Secure Storage** - All data stored locally and encrypted

## 🚀 How It Works

### **Setup (One-time, 2 minutes)**
1. Run AppLocker
2. Scan QR code with Google Authenticator
3. Click "Complete Setup" - **No PIN needed!**

### **Lock Applications**
1. Click "Lock New Apps"
2. Browse/search through 200+ detected apps
3. Select app → Confirm lock
4. App is immediately blocked from running

### **Unlock Applications**
1. Select locked app from main interface
2. Enter 6-digit code from Google Authenticator
3. App unlocks for 1 hour automatically

### **Real-time Protection**
- Background service monitors all running processes
- Locked apps are immediately terminated when detected
- User gets notification when blocked app is attempted

## 💻 Installation

### Quick Start (Recommended)
1. Download latest release from [GitHub Releases](https://github.com/Srihaas007/Applocker/releases)
2. Extract and run `AppLocker.exe`
3. **Run as Administrator** for full app detection

### From Source
```bash
# Clone repository
git clone https://github.com/Srihaas007/Applocker.git
cd Applocker

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Build Your Own
```bash
# Install build tools
pip install pyinstaller

# Build executable
deploy.bat  # Windows
# or
./deploy.sh  # Linux/Mac
```

## 🎮 Usage Scenarios

### **Parental Controls**
- Lock games during homework time
- Block social media apps
- Control access to inappropriate content

### **Work Productivity**
- Block distracting apps during work hours
- Secure work-related applications
- Prevent unauthorized access to company tools

### **Personal Security**
- Protect banking/financial apps
- Secure messaging applications
- Lock password managers

### **Shared Computers**
- Protect personal apps on family computers
- Secure private data
- Control access in public spaces

## 🔒 Security Features

1. **Google Authenticator 2FA**: Industry-standard TOTP authentication
2. **Real-time Process Monitoring**: Background service actively blocks apps
3. **Local Storage Only**: No cloud dependencies or data transmission
4. **Encrypted Configuration**: All settings stored securely
5. **Audit Trail**: Comprehensive logging for security monitoring
6. **Temporary Unlocking**: Apps auto-lock after 1 hour for security

## 📁 Project Structure
```
AppLocker/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── README.md                 # This documentation
├── app/
│   ├── config.py             # Configuration management
│   ├── auth.py               # Authentication logic
│   ├── gui.py                # User interface
│   ├── process_manager.py    # App blocking engine
│   ├── app_lock.py          # App discovery
│   └── logging.py           # Logging system
├── data/                     # User data (created at runtime)
│   ├── user_data.txt        # Google Authenticator secret
│   └── locked_apps.json     # Locked applications list
└── logs/                     # Application logs
    └── app_logs.log         # Activity log
```

## 🛠️ Technical Details

### Requirements
- **OS**: Windows 10/11 (Administrator privileges recommended)
- **Python**: 3.8+ (if running from source)
- **Mobile**: Google Authenticator app

### Dependencies
- `pyotp`: TOTP authentication
- `qrcode`: QR code generation 
- `Pillow`: Image processing
- `psutil`: Process monitoring
- `tkinter`: GUI framework (built into Python)

### Architecture
- **Main Thread**: GUI and user interaction
- **Background Thread**: Real-time process monitoring
- **Event-driven**: Responds to app launch attempts
- **Stateless**: No persistent connections or services

## ⚠️ Important Notes

- **Run as Administrator** for complete app detection and blocking
- **Google Authenticator** app required on mobile device
- **Temporary Unlocks** last 1 hour for convenience
- **Process Monitoring** may use minimal CPU (~1-2%)
- **Windows Only** - Linux/Mac support planned

## 🐛 Troubleshooting

### App Not Detected
- Ensure AppLocker runs as Administrator
- Check if app is a Windows Store (UWP) app
- Try alternative app names or executable files

### QR Code Won't Scan
- Ensure good lighting when scanning
- Try manual entry using the displayed key
- Check Google Authenticator app is updated

### App Still Opens
- Wait 2-3 seconds for monitoring to detect
- Check app name matches exactly
- Restart AppLocker service

### Performance Issues
- Adjust monitoring interval in config
- Close other security software temporarily
- Check Windows Defender exclusions

## 📈 Changelog

### v2.0.0 (Latest) - Major Overhaul
- ✅ **Removed PIN requirement** - Only Google Authenticator needed
- ✅ **Real app blocking** - Apps actually prevented from running  
- ✅ **Improved UI** - Better app discovery and search
- ✅ **Background monitoring** - Real-time process blocking
- ✅ **Temporary unlocks** - 1-hour automatic unlock duration
- ✅ **Enhanced security** - Better process detection and blocking

### v1.0.0 - Initial Release
- Basic app locking functionality
- PIN + 2FA authentication
- Simple GUI interface
- Basic logging system

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/Srihaas007/Applocker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Srihaas007/Applocker/discussions)
- **Email**: Create an issue for direct contact

## ⭐ Star History

If this project helped you, please consider giving it a star! ⭐

---

**Made with ❤️ for Windows security and productivity**

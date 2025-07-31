# AppLocker Email Reset Feature

## Overview
The reset authenticator feature allows users to reset their Google Authenticator setup via email verification when they lose access to their QR code or authenticator app.

## Email Configuration Setup

### For Gmail Users:
1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "AppLocker"
3. **Update Configuration**:
   - Open `app/email_config.py`
   - Set `EMAIL_FROM` to your Gmail address
   - Set `EMAIL_PASSWORD` to your generated app password (NOT your regular password)
   - Set `EMAIL_ENABLED` to `True`

### For Other Email Providers:
Update the SMTP settings in `email_config.py`:
- **Outlook/Hotmail**: `smtp-mail.outlook.com`, port 587
- **Yahoo**: `smtp.mail.yahoo.com`, port 587
- **Custom SMTP**: Update server and port accordingly

## Security Features
- **OTP Expiration**: 15 minutes by default
- **One-time Use**: Each OTP can only be used once
- **Automatic Cleanup**: Expired OTPs are automatically removed
- **Email Verification**: Only the registered user email can receive reset codes

## How It Works
1. User clicks "Reset Authenticator" in setup window
2. System sends 6-digit OTP to registered email
3. User enters OTP to verify identity  
4. New secret key and QR code are generated
5. Old authenticator setup becomes invalid

## Files
- `app/email_service.py` - Core email functionality
- `app/email_config.py` - Configuration (UPDATE THIS)
- `app/gui.py` - Reset UI integration
- `app/data/reset_otps.json` - Temporary OTP storage

## Testing
Before deploying, test email functionality:
1. Configure email settings
2. Use the reset feature with a test email
3. Verify OTP delivery and functionality

## Security Notes
- Never commit real email passwords to git
- Use app passwords, not regular passwords
- Consider using environment variables for production
- Monitor email sending logs for suspicious activity

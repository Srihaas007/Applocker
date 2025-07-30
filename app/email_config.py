# Email Configuration for AppLocker
# 
# IMPORTANT: Configure these settings before using the reset feature
# 
# For Gmail:
# 1. Enable 2-factor authentication on your Gmail account
# 2. Generate an "App Password" (not your regular password)
# 3. Use the app password in EMAIL_PASSWORD below
#
# For other email providers, update SMTP_SERVER and SMTP_PORT accordingly

# Email settings - UPDATE THESE WITH YOUR ACTUAL EMAIL CREDENTIALS
EMAIL_CONFIG = {
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "EMAIL_FROM": "your-applocker-email@gmail.com",  # Your email address
    "EMAIL_PASSWORD": "your-app-password-here",      # Your app password (NOT regular password)
    "EMAIL_ENABLED": False  # Set to True after configuring email
}

# Email templates
EMAIL_TEMPLATES = {
    "RESET_SUBJECT": "AppLocker - Authentication Reset Request",
    "RESET_BODY": """Dear AppLocker User,

You have requested to reset your Google Authenticator setup for AppLocker.

Your One-Time Password (OTP) is: {otp}

This OTP will expire in 15 minutes.

To reset your authenticator:
1. Open AppLocker
2. Click "Reset Authenticator" 
3. Enter this OTP: {otp}
4. Scan the new QR code with Google Authenticator

If you did not request this reset, please ignore this email.

Best regards,
AppLocker Security Team

Generated at: {timestamp}
"""
}

# Security settings
SECURITY_CONFIG = {
    "OTP_LENGTH": 6,
    "OTP_EXPIRY_MINUTES": 15,
    "MAX_OTP_ATTEMPTS": 3
}

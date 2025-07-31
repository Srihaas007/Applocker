import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json
import os
from app.logging import log_event, log_error
from app.config import USER_DATA_FILE
from app.email_config import EMAIL_CONFIG, EMAIL_TEMPLATES, SECURITY_CONFIG

# OTP storage file
OTP_FILE = os.path.join(os.path.dirname(__file__), "data", "reset_otps.json")

def generate_otp(length=None):
    """Generate a random OTP"""
    if length is None:
        length = SECURITY_CONFIG["OTP_LENGTH"]
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def save_otp(email, otp):
    """Save OTP with expiration time"""
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(OTP_FILE), exist_ok=True)
        
        # Load existing OTPs
        try:
            with open(OTP_FILE, "r", encoding="utf-8") as file:
                otps = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            otps = {}
        
        # Add new OTP with configurable expiration
        expiry_minutes = SECURITY_CONFIG["OTP_EXPIRY_MINUTES"]
        expiry = (datetime.now() + timedelta(minutes=expiry_minutes)).isoformat()
        otps[email] = {
            "otp": otp,
            "expiry": expiry,
            "used": False
        }
        
        # Save back to file
        with open(OTP_FILE, "w", encoding="utf-8") as file:
            json.dump(otps, file, indent=2)
        
        log_event(f"OTP saved for {email}, expires at {expiry}")
        return True
        
    except Exception as e:
        log_error(f"Failed to save OTP for {email}: {e}")
        return False

def verify_otp(email, entered_otp):
    """Verify OTP and mark as used"""
    try:
        with open(OTP_FILE, "r", encoding="utf-8") as file:
            otps = json.load(file)
        
        if email not in otps:
            log_error(f"No OTP found for {email}")
            return False
        
        otp_data = otps[email]
        
        # Check if already used
        if otp_data.get("used", False):
            log_error(f"OTP already used for {email}")
            return False
        
        # Check expiry
        expiry = datetime.fromisoformat(otp_data["expiry"])
        if datetime.now() > expiry:
            log_error(f"OTP expired for {email}")
            return False
        
        # Check OTP match
        if otp_data["otp"] != entered_otp:
            log_error(f"Invalid OTP for {email}")
            return False
        
        # Mark as used
        otps[email]["used"] = True
        with open(OTP_FILE, "w", encoding="utf-8") as file:
            json.dump(otps, file, indent=2)
        
        log_event(f"OTP verified successfully for {email}")
        return True
        
    except Exception as e:
        log_error(f"Failed to verify OTP for {email}: {e}")
        return False

def send_reset_email(user_email, otp):
    """Send password reset email with OTP"""
    try:
        # Check if email is configured
        if not EMAIL_CONFIG["EMAIL_ENABLED"]:
            log_error("Email service is not configured. Please update email_config.py")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["EMAIL_FROM"]
        msg['To'] = user_email
        msg['Subject'] = EMAIL_TEMPLATES["RESET_SUBJECT"]
        
        # Email body with template
        body = EMAIL_TEMPLATES["RESET_BODY"].format(
            otp=otp,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(EMAIL_CONFIG["SMTP_SERVER"], EMAIL_CONFIG["SMTP_PORT"])
        server.starttls()
        server.login(EMAIL_CONFIG["EMAIL_FROM"], EMAIL_CONFIG["EMAIL_PASSWORD"])
        
        text = msg.as_string()
        server.sendmail(EMAIL_CONFIG["EMAIL_FROM"], user_email, text)
        server.quit()
        
        log_event(f"Reset email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        log_error(f"Failed to send reset email to {user_email}: {e}")
        return False

def send_test_email(user_email):
    """Send a test email to verify email configuration"""
    try:
        otp = "123456"  # Test OTP
        return send_reset_email(user_email, otp)
    except Exception as e:
        log_error(f"Test email failed for {user_email}: {e}")
        return False

def cleanup_expired_otps():
    """Remove expired OTPs from storage"""
    try:
        if not os.path.exists(OTP_FILE):
            return
        
        with open(OTP_FILE, "r", encoding="utf-8") as file:
            otps = json.load(file)
        
        # Remove expired OTPs
        current_time = datetime.now()
        cleaned_otps = {}
        
        for email, otp_data in otps.items():
            expiry = datetime.fromisoformat(otp_data["expiry"])
            if current_time <= expiry:
                cleaned_otps[email] = otp_data
        
        # Save cleaned data
        with open(OTP_FILE, "w", encoding="utf-8") as file:
            json.dump(cleaned_otps, file, indent=2)
        
        removed_count = len(otps) - len(cleaned_otps)
        if removed_count > 0:
            log_event(f"Cleaned up {removed_count} expired OTPs")
        
    except Exception as e:
        log_error(f"Failed to cleanup expired OTPs: {e}")

def get_user_email_from_storage():
    """Get the current user's email from storage"""
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as file:
            content = file.read().strip()
        
        # Parse the format: secret_key|email
        if '|' in content:
            _, email = content.split('|', 1)
            return email
        else:
            return None
            
    except Exception as e:
        log_error(f"Failed to get user email from storage: {e}")
        return None

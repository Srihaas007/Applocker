import json
import pyotp
from tkinter import simpledialog, messagebox
from app.logging import log_event, log_error
from app.config import USER_DATA_FILE, LOCKED_APPS_FILE, TOTP_WINDOW
import bcrypt

# Function to save secret key with user info to a file
def save_secret_to_db(secret_key, user_email="user@applocker.com"):
    # Validate secret key is proper base32
    try:
        import base64
        base64.b32decode(secret_key, casefold=True)
    except Exception as e:
        log_error(f"Invalid secret key format: {e}")
        raise ValueError("Invalid secret key format")
        
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"{secret_key}\n")  # Save the secret key
        f.write(f"{user_email}\n")  # Save user email
    log_event(f"Secret key saved successfully for user: {user_email}")

# Function to load user data from file
def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) >= 1:
                secret_key = lines[0].strip()
                user_email = lines[1].strip() if len(lines) >= 2 else "unknown"
                
                # Validate secret key format
                try:
                    import base64
                    base64.b32decode(secret_key, casefold=True)
                    return secret_key, user_email
                except Exception as e:
                    log_error(f"Invalid secret key in storage: {e}")
                    return None, None
                    
    except FileNotFoundError:
        log_error("User data file not found")
    except Exception as e:
        log_error(f"Error loading user data: {e}")
    return None, None

# Function to get app status from locked apps file
def get_app_status(app_name):
    try:
        with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
            locked_apps = json.load(file)
            return locked_apps.get(app_name, False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

# Function to verify TOTP code entered by the user
def verify_totp(secret, entered_code):
    totp = pyotp.TOTP(secret)
    # Use a wider window for more flexibility
    is_valid = totp.verify(entered_code, valid_window=TOTP_WINDOW)
    log_event(f"TOTP verification - Valid: {is_valid}")
    return is_valid

# Function to verify the entered PIN against the stored hashed PIN
def verify_pin(stored_hashed_pin, entered_pin):
    return bcrypt.checkpw(entered_pin.encode('utf-8'), stored_hashed_pin)

def unlock_app(app_name=None):
    if app_name is None:
        # If no app name provided, show a simple unlock interface
        try:
            from app.gui import show_unlock_interface
            show_unlock_interface()
        except ImportError:
            messagebox.showerror("Error", "Unable to load interface")
        return
    
    # Check if app is locked
    if not get_app_status(app_name):
        messagebox.showerror("Error", "App is not locked.")
        return
    
    # Load user data to get secret key
    secret_key, user_email = load_user_data()
    
    if not secret_key:
        messagebox.showerror("Error", "User data not found. Please set up the app first.")
        return
    
    # Only ask for 2FA code
    entered_code = simpledialog.askstring("2FA Verification", 
                                        f"Enter 2FA code from Google Authenticator\n"
                                        f"User: {user_email}\n"
                                        f"App: {app_name}")
    
    if not entered_code:
        return
        
    if verify_totp(secret_key, entered_code):
        messagebox.showinfo("Success", f"{app_name} unlocked successfully!\nUnlocked for 1 hour.")
        log_event(f"App {app_name} unlocked successfully for user {user_email}")
        # Temporarily unlock the app for 1 hour
        from app.process_manager import unlock_app_temporarily
        unlock_app_temporarily(app_name, 60)
    else:
        messagebox.showerror("Invalid 2FA Code", "The 2FA code you entered is incorrect.\nPlease try again.")
        log_error(f"Invalid 2FA code for app {app_name} by user {user_email}")

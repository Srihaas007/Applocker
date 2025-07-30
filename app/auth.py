import json
import pyotp
from tkinter import simpledialog, messagebox
from app.logging import log_event, log_error
import bcrypt

# Function to save the PIN and secret key to a file
def save_pin_to_db(hashed_pin, secret_key):
    with open("user_data.txt", "w", encoding="utf-8") as f:
        f.write(f"{hashed_pin.decode()}\n")  # Save the hashed PIN (decoded from bytes)
        f.write(f"{secret_key}\n")  # Save the secret key
    log_event("PIN and secret key saved successfully")

# Function to load user data from file
def load_user_data():
    try:
        with open("user_data.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                hashed_pin = lines[0].strip()
                secret_key = lines[1].strip()
                return hashed_pin, secret_key
    except FileNotFoundError:
        log_error("User data file not found")
    return None, None

# Function to get app PIN from locked apps file
def get_app_pin(app_name):
    try:
        with open("locked_apps.json", "r", encoding="utf-8") as file:
            locked_apps = json.load(file)
            return locked_apps.get(app_name)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Function to verify TOTP code entered by the user
def verify_totp(secret, entered_code):
    totp = pyotp.TOTP(secret)
    generated_code = totp.now()  # Generate the TOTP code for current time
    log_event(f"Generated code: {generated_code}")
    is_valid = totp.verify(entered_code)  # Check if the entered code is correct
    log_event(f"Entered code: {entered_code} - Valid: {is_valid}")
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
    
    stored_hashed_pin = get_app_pin(app_name)
    
    if not stored_hashed_pin:
        messagebox.showerror("Error", "App is not locked.")
        return
    
    entered_pin = simpledialog.askstring("PIN Entry", f"Enter PIN for {app_name}:", show="*")
    
    if not entered_pin:
        return
    
    # Load user data to get secret key
    _, secret_key = load_user_data()
    
    if not secret_key:
        messagebox.showerror("Error", "User data not found. Please set up the app first.")
        return
    
    if verify_pin(stored_hashed_pin.encode(), entered_pin):
        entered_code = simpledialog.askstring("2FA Verification", "Enter the 2FA code from Google Authenticator:")
        if entered_code and verify_totp(secret_key, entered_code):
            messagebox.showinfo("Success", f"{app_name} unlocked successfully!")
            log_event(f"App {app_name} unlocked successfully")
        else:
            messagebox.showerror("Invalid 2FA Code", "The 2FA code you entered is incorrect.")
            log_error(f"Invalid 2FA code for app {app_name}")
    else:
        messagebox.showerror("Invalid PIN", "The PIN entered is incorrect.")
        log_error(f"Invalid PIN for app {app_name}")

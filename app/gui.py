import json
import pyotp
import qrcode
import os
import sys
import subprocess
import shutil
import random
import string
from tkinter import *
from tkinter import messagebox
from PIL import ImageTk, Image
from app.logging import log_event, log_error
from app.auth import save_secret_to_db, unlock_app
from app.app_lock import get_installed_apps
from app.config import QR_CODE_FILE, LOCKED_APPS_FILE, WINDOW_TITLE
from app.email_service import (
    generate_otp, save_otp, verify_otp, send_reset_email, 
    cleanup_expired_otps, get_user_email_from_storage
)

# Function to generate a secret key for Google Authenticator
def generate_secret_key():
    secret = pyotp.random_base32()  # Generate a random secret key
    log_event(f"Generated new secret key: {secret}")
    return secret

# Function to generate master backup keys
def generate_master_key():
    """Generate a 16-character master key"""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(16))

# Function to save master keys
def save_master_keys(keys, user_email):
    """Save master keys to secure storage"""
    try:
        from app.config import USER_DATA_FILE
        import json
        
        # Load existing data
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as file:
                data = file.read().strip().split('\n')
                secret = data[0] if len(data) > 0 else ""
                email = data[1] if len(data) > 1 else ""
        except:
            secret, email = "", ""
        
        # Create master keys file
        master_keys_file = USER_DATA_FILE.replace("user_data.txt", "master_keys.json")
        master_data = {
            "email": user_email,
            "keys": keys,
            "used_keys": []
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(master_keys_file), exist_ok=True)
        
        with open(master_keys_file, "w", encoding="utf-8") as file:
            json.dump(master_data, file, indent=2)
        
        log_event(f"Master keys saved for {user_email}")
        return True
        
    except Exception as e:
        log_error(f"Failed to save master keys: {e}")
        return False

# Function to verify master key
def verify_master_key(key, user_email):
    """Verify if a master key is valid and unused"""
    try:
        from app.config import USER_DATA_FILE
        import json
        
        master_keys_file = USER_DATA_FILE.replace("user_data.txt", "master_keys.json")
        
        if not os.path.exists(master_keys_file):
            return False
        
        with open(master_keys_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        if data.get("email") != user_email:
            return False
        
        if key in data.get("used_keys", []):
            return False  # Key already used
        
        if key in data.get("keys", []):
            # Mark key as used
            data["used_keys"].append(key)
            
            with open(master_keys_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            
            log_event(f"Master key used for {user_email}")
            return True
        
        return False
        
    except Exception as e:
        log_error(f"Failed to verify master key: {e}")
        return False

# Function to generate a QR Code for Google Authenticator setup
def generate_qr_code(secret, email):
    try:
        # Ensure assets directory exists
        assets_dir = os.path.dirname(QR_CODE_FILE)
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir, exist_ok=True)
            log_event(f"Created assets directory: {assets_dir}")
        
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(email, issuer_name="AppLocker")
        log_event(f"Generated TOTP URI for {email}")
        
        # Create QR code with qrcode library
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction
            box_size=10,  # Larger box size for better quality
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # Create image with high contrast and larger size
        img = qr.make_image(fill_color="black", back_color="white")
        # Ensure minimum size for the QR code
        img = img.resize((300, 300), Image.Resampling.LANCZOS)
        
        # Save the image
        img.save(QR_CODE_FILE)
        log_event(f"QR code saved successfully to {QR_CODE_FILE}")
        
        # Verify file was created
        if os.path.exists(QR_CODE_FILE):
            file_size = os.path.getsize(QR_CODE_FILE)
            log_event(f"QR code file verified: {file_size} bytes")
            return QR_CODE_FILE
        else:
            raise FileNotFoundError("QR code file was not created")
        
    except ImportError as e:
        log_error(f"Missing qrcode library: {e}")
        raise ImportError("qrcode library not installed. Run: pip install qrcode")
    except Exception as e:
        log_error(f"Failed to generate QR code: {e}")
        raise RuntimeError(f"QR code generation failed: {str(e)}")

# Function to handle user setup for 2FA authentication - NEW WIZARD DESIGN
def user_setup():
    setup_win = Tk()
    setup_win.title(f"{WINDOW_TITLE} - Setup Wizard")
    setup_win.geometry("500x700")  # Increased height significantly for navigation
    setup_win.resizable(False, False)  # Fixed size for consistent experience
    setup_win.configure(bg="#f0f0f0")
    setup_win.minsize(500, 700)  # Enforce minimum size
    
    # Center the window
    setup_win.update_idletasks()
    x = (setup_win.winfo_screenwidth() // 2) - (500 // 2)
    y = (setup_win.winfo_screenheight() // 2) - (700 // 2)
    setup_win.geometry(f"500x700+{x}+{y}")
    
    # Global variables for wizard state
    current_step = 0
    total_steps = 5
    user_email = ""
    secret_key = None
    master_keys = []
    
    # Main container
    main_frame = Frame(setup_win, bg="#f0f0f0", padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Header with progress
    header_frame = Frame(main_frame, bg="#2c3e50", height=80)
    header_frame.pack(fill=X, pady=(0, 20))
    header_frame.pack_propagate(False)
    
    # Progress bar
    progress_canvas = Canvas(header_frame, height=6, bg="#34495e", highlightthickness=0)
    progress_canvas.pack(fill=X, padx=20, pady=(25, 5))
    
    title_label = Label(header_frame, text="AppLocker Setup Wizard", 
                       font=("Segoe UI", 16, "bold"), fg="white", bg="#2c3e50")
    title_label.pack(pady=(5, 15))
    
    # Step indicator
    step_label = Label(header_frame, text="Step 1 of 5: Welcome", 
                      font=("Segoe UI", 10), fg="#bdc3c7", bg="#2c3e50")
    step_label.pack()
    
    # Simple, clear layout - content area with fixed navigation at bottom
    # Content area
    content_frame = Frame(main_frame, bg="white", relief="solid", bd=1)
    content_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
    
    def update_progress():
        progress_canvas.delete("all")
        progress_width = 460  # Total width
        step_width = progress_width / total_steps
        filled_width = step_width * (current_step + 1)
        
        # Background
        progress_canvas.create_rectangle(0, 0, progress_width, 6, fill="#34495e", outline="")
        # Progress
        progress_canvas.create_rectangle(0, 0, filled_width, 6, fill="#27ae60", outline="")
        
        # Update labels
        step_names = ["Welcome", "Enter Email", "Generate QR", "Verify Setup", "Complete"]
        title_label.config(text=f"AppLocker Setup Wizard")
        step_label.config(text=f"Step {current_step + 1} of {total_steps}: {step_names[current_step]}")
    
    def clear_content():
        for widget in content_frame.winfo_children():
            widget.destroy()
    
    def show_step_1_welcome():
        clear_content()
        
        # Create main container with fixed height for consistent layout
        page_container = Frame(content_frame, bg="white")
        page_container.pack(fill=BOTH, expand=True)
        
        # Top content area
        content_area = Frame(page_container, bg="white", padx=30, pady=30)
        content_area.pack(fill=BOTH, expand=True)
        
        # Welcome icon
        Label(content_area, text="🔐", font=("Segoe UI", 48), bg="white").pack(pady=(0, 20))
        
        Label(content_area, text="Welcome to AppLocker!", 
              font=("Segoe UI", 18, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 10))
        
        Label(content_area, text="Secure your applications with Google Authenticator", 
              font=("Segoe UI", 11), bg="white", fg="#7f8c8d").pack(pady=(0, 20))
        
        # Features list
        features_frame = Frame(content_area, bg="white")
        features_frame.pack(fill=X, pady=(0, 20))
        
        features = [
            "🛡️ Lock any Windows application",
            "📱 Use Google Authenticator for security", 
            "🔑 Get backup master keys for emergencies",
            "⚡ Quick unlock sessions",
            "🔄 Easy reset with email verification"
        ]
        
        for feature in features:
            Label(features_frame, text=feature, font=("Segoe UI", 10), 
                  bg="white", fg="#2c3e50", anchor="w").pack(fill=X, pady=2)
        
        Label(content_area, text="Click 'Next' to begin setup", 
              font=("Segoe UI", 10), bg="white", fg="#7f8c8d").pack(pady=(10, 0))
              
        # NAVIGATION BAR - fixed at bottom
        nav_bar = Frame(page_container, bg="#f8f9fa", height=70, relief="solid", bd=1)
        nav_bar.pack(fill=X, side=BOTTOM, pady=(10, 0))
        nav_bar.pack_propagate(False)
        
        # Center the buttons
        btn_container = Frame(nav_bar, bg="#f8f9fa")
        btn_container.place(relx=0.5, rely=0.5, anchor=CENTER)
        
        # Next button only (first step)
        next_button = Button(btn_container, text="NEXT →", 
                           command=lambda: next_step(),
                           font=("Segoe UI", 12, "bold"), bg="#28a745", fg="white",
                           relief="raised", padx=40, pady=10, bd=2)
        next_button.pack()
    
    def show_step_2_email():
        clear_content()
        
        # Create main container with fixed layout
        page_container = Frame(content_frame, bg="white")
        page_container.pack(fill=BOTH, expand=True)
        
        # Top content area
        content_area = Frame(page_container, bg="white", padx=30, pady=30)
        content_area.pack(fill=BOTH, expand=True)
        
        Label(content_area, text="📧", font=("Segoe UI", 36), bg="white").pack(pady=(0, 20))
        
        Label(content_area, text="Enter Your Email", 
              font=("Segoe UI", 16, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 10))
        
        Label(content_area, text="This will identify your AppLocker account and enable recovery", 
              font=("Segoe UI", 10), bg="white", fg="#7f8c8d", wraplength=400).pack(pady=(0, 20))
        
        # Email input with modern styling
        Label(content_area, text="Email Address:", 
              font=("Segoe UI", 10, "bold"), bg="white", fg="#2c3e50").pack(anchor="w")
        
        email_var = StringVar()
        email_entry = Entry(content_area, textvariable=email_var, font=("Segoe UI", 12), 
                           width=35, relief="solid", bd=1)
        email_entry.pack(pady=(5, 20), ipady=8)
        email_entry.insert(0, "user@example.com")
        email_entry.focus()
        
        # Validation feedback
        feedback_label = Label(content_area, text="", font=("Segoe UI", 9), bg="white")
        feedback_label.pack(pady=(0, 10))
        
        def validate_email():
            nonlocal user_email
            email = email_var.get().strip()
            
            if not email:
                feedback_label.config(text="Please enter an email address", fg="red")
                return False
            
            if "@" not in email:
                feedback_label.config(text="⚠️ This doesn't look like an email address", fg="orange")
            else:
                feedback_label.config(text="✅ Email looks good!", fg="green")
            
            user_email = email
            return True
        
        email_var.trace("w", lambda *args: validate_email())
        
        # Store validation function for next button validation
        content_frame.validate_email = validate_email
        
        # NAVIGATION BAR - fixed at bottom
        nav_bar = Frame(page_container, bg="#f8f9fa", height=70, relief="solid", bd=1)
        nav_bar.pack(fill=X, side=BOTTOM, pady=(10, 0))
        nav_bar.pack_propagate(False)
        
        # Center the buttons
        btn_container = Frame(nav_bar, bg="#f8f9fa")
        btn_container.place(relx=0.5, rely=0.5, anchor=CENTER)
        
        # Back button
        back_button = Button(btn_container, text="← BACK", 
                            command=lambda: prev_step(),
                            font=("Segoe UI", 12, "bold"), bg="#6c757d", fg="white",
                            relief="raised", padx=30, pady=10, bd=2)
        back_button.pack(side=LEFT, padx=10)
        
        # Next button
        next_button = Button(btn_container, text="NEXT →", 
                           command=lambda: next_step(),
                           font=("Segoe UI", 12, "bold"), bg="#28a745", fg="white",
                           relief="raised", padx=30, pady=10, bd=2)
        next_button.pack(side=LEFT, padx=10)
    
    def show_step_3_generate_qr():
        clear_content()
        
        # Create main container with fixed layout
        page_container = Frame(content_frame, bg="white")
        page_container.pack(fill=BOTH, expand=True)
        
        # ALWAYS VISIBLE NAVIGATION AT THE TOP
        top_nav_frame = Frame(page_container, bg="#ff5722", relief="solid", bd=4)
        top_nav_frame.pack(fill=X, pady=(0, 10))
        
        Label(top_nav_frame, text="NAVIGATION (ALWAYS VISIBLE)", 
              font=("Segoe UI", 14, "bold"), bg="#ff5722", fg="white").pack(pady=5)
        
        nav_buttons_frame = Frame(top_nav_frame, bg="#ff5722")
        nav_buttons_frame.pack(pady=10)
        
        Button(nav_buttons_frame, text="⬅️ BACK TO EMAIL", 
               command=lambda: prev_step(),
               font=("Segoe UI", 14, "bold"), bg="#d32f2f", fg="white",
               relief="raised", padx=20, pady=10, bd=3).pack(side=LEFT, padx=20)
               
        Button(nav_buttons_frame, text="NEXT TO VERIFY ➡️", 
               command=lambda: next_step(),
               font=("Segoe UI", 14, "bold"), bg="#388e3c", fg="white",
               relief="raised", padx=20, pady=10, bd=3).pack(side=RIGHT, padx=20)
        
        # Content area with scrollable capability
        content_area = Frame(page_container, bg="white", padx=30, pady=10)
        content_area.pack(fill=BOTH, expand=True)
        
        Label(content_area, text="📱", font=("Segoe UI", 28), bg="white").pack(pady=(0, 5))
        
        Label(content_area, text="Generate QR Code", 
              font=("Segoe UI", 14, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 5))
        
        Label(content_area, text=f"Setting up authenticator for: {user_email}", 
              font=("Segoe UI", 9), bg="white", fg="#7f8c8d").pack(pady=(0, 10))
        
        # QR Code display area - smaller to save space
        qr_display_frame = Frame(content_area, bg="#f8f9fa", relief="solid", bd=1, width=180, height=180)
        qr_display_frame.pack(pady=(0, 5))
        qr_display_frame.pack_propagate(False)
        
        qr_label = Label(qr_display_frame, text="Click 'Generate QR Code' below", 
                        font=("Segoe UI", 8), bg="#f8f9fa", fg="#6c757d")
        qr_label.place(relx=0.5, rely=0.5, anchor=CENTER)
        
        # Generate button
        def generate_qr():
            nonlocal secret_key
            
            try:
                qr_label.config(text="Generating...", fg="#007bff")
                setup_win.update()
                
                secret_key = generate_secret_key()
                qr_code_path = generate_qr_code(secret_key, user_email)
                
                if os.path.exists(qr_code_path):
                    img = Image.open(qr_code_path)
                    img = img.resize((170, 170), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    qr_label.config(image=photo, text="")
                    qr_label.image = photo
                    
                    # Show manual key
                    manual_key_label.config(text=secret_key)
                    
                    messagebox.showinfo("QR Code Ready!", 
                                       "1. Install Google Authenticator on your phone\n"
                                       "2. Scan the QR code above\n"
                                       "3. Use the ORANGE navigation buttons at the top!")
                else:
                    qr_label.config(text="❌ Generation failed", fg="red")
                    
            except Exception as e:
                qr_label.config(text="❌ Error generating QR code", fg="red")
                messagebox.showerror("Error", f"Failed to generate QR code: {str(e)}")
        
        Button(content_area, text="Generate QR Code", command=generate_qr,
               font=("Segoe UI", 9, "bold"), bg="#007bff", fg="white", 
               relief="flat", padx=15, pady=6).pack(pady=(0, 10))
        
        # Manual key display - compact
        Label(content_area, text="Manual Key:", 
              font=("Segoe UI", 8, "bold"), bg="white", fg="#2c3e50").pack()
        
        manual_key_label = Label(content_area, text="Generate QR code first", 
                                font=("Courier", 7), bg="#f8f9fa", fg="#6c757d", 
                                relief="solid", bd=1, padx=5, pady=3)
        manual_key_label.pack(fill=X, pady=(2, 10))
        
        # Store references
        content_frame.secret_key = lambda: secret_key
    
    def show_step_4_verify():
        clear_content()
        
        if not secret_key:
            messagebox.showerror("Error", "Please generate QR code first!")
            return
        
        # Create main container with fixed layout
        page_container = Frame(content_frame, bg="white")
        page_container.pack(fill=BOTH, expand=True)
        
        # Top content area
        content_area = Frame(page_container, bg="white", padx=30, pady=30)
        content_area.pack(fill=BOTH, expand=True)
        
        Label(content_area, text="🔐", font=("Segoe UI", 36), bg="white").pack(pady=(0, 15))
        
        Label(content_area, text="Verify Setup", 
              font=("Segoe UI", 16, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 10))
        
        Label(content_area, text="Enter the 6-digit code from your Google Authenticator app", 
              font=("Segoe UI", 10), bg="white", fg="#7f8c8d", wraplength=400).pack(pady=(0, 25))
        
        # Code input
        code_var = StringVar()
        code_entry = Entry(content_area, textvariable=code_var, font=("Segoe UI", 18, "bold"), 
                          width=10, justify=CENTER, relief="solid", bd=2)
        code_entry.pack(pady=(0, 20), ipady=10)
        code_entry.focus()
        
        # Verification feedback
        verify_feedback = Label(content_area, text="", font=("Segoe UI", 10), bg="white")
        verify_feedback.pack(pady=(0, 20))
        
        def verify_code():
            code = code_var.get().strip()
            
            if len(code) != 6 or not code.isdigit():
                verify_feedback.config(text="Please enter a 6-digit code", fg="red")
                return False
            
            try:
                totp = pyotp.TOTP(secret_key)
                
                if totp.verify(code, valid_window=2):  # Allow 2 windows for clock skew
                    verify_feedback.config(text="✅ Verification successful!", fg="green")
                    
                    # Generate master keys
                    nonlocal master_keys
                    master_keys = [generate_master_key() for _ in range(6)]
                    
                    messagebox.showinfo("Verification Successful!", 
                                       "🎉 Your Google Authenticator is working correctly!\n\n"
                                       "Next: You'll receive backup master keys for emergencies.")
                    return True
                else:
                    verify_feedback.config(text="❌ Invalid code. Please try again.", fg="red")
                    return False
                    
            except Exception as e:
                verify_feedback.config(text="❌ Verification error", fg="red")
                return False
        
        Button(content_area, text="Verify Code", command=verify_code,
               font=("Segoe UI", 10, "bold"), bg="#28a745", fg="white", 
               relief="flat", padx=20, pady=8).pack(pady=(0, 30))
        
        # Store verification function
        content_frame.verify_code = verify_code
        
        # NAVIGATION BAR - fixed at bottom
        nav_bar = Frame(page_container, bg="#f8f9fa", height=70, relief="solid", bd=1)
        nav_bar.pack(fill=X, side=BOTTOM, pady=(10, 0))
        nav_bar.pack_propagate(False)
        
        # Center the buttons
        btn_container = Frame(nav_bar, bg="#f8f9fa")
        btn_container.place(relx=0.5, rely=0.5, anchor=CENTER)
        
        # Back button
        back_button = Button(btn_container, text="← BACK", 
                            command=lambda: prev_step(),
                            font=("Segoe UI", 12, "bold"), bg="#6c757d", fg="white",
                            relief="raised", padx=30, pady=10, bd=2)
        back_button.pack(side=LEFT, padx=10)
        
        # Next button
        next_button = Button(btn_container, text="NEXT →", 
                           command=lambda: next_step(),
                           font=("Segoe UI", 12, "bold"), bg="#28a745", fg="white",
                           relief="raised", padx=30, pady=10, bd=2)
        next_button.pack(side=LEFT, padx=10)
    
    def show_step_5_complete():
        clear_content()
        
        # Create main container with fixed layout
        page_container = Frame(content_frame, bg="white")
        page_container.pack(fill=BOTH, expand=True)
        
        # Top content area
        content_area = Frame(page_container, bg="white", padx=30, pady=30)
        content_area.pack(fill=BOTH, expand=True)
        
        Label(content_area, text="🎉", font=("Segoe UI", 36), bg="white").pack(pady=(0, 15))
        
        Label(content_area, text="Setup Complete!", 
              font=("Segoe UI", 16, "bold"), bg="white", fg="#28a745").pack(pady=(0, 10))
        
        Label(content_area, text=f"AppLocker is ready for {user_email}", 
              font=("Segoe UI", 10), bg="white", fg="#7f8c8d").pack(pady=(0, 20))
        
        # Master keys display
        Label(content_area, text="🔑 Master Backup Keys", 
              font=("Segoe UI", 12, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 10))
        
        Label(content_area, text="Save these keys safely! Use them if you lose access to your authenticator:", 
              font=("Segoe UI", 9), bg="white", fg="#e74c3c", wraplength=400).pack(pady=(0, 10))
        
        keys_frame = Frame(content_area, bg="#fff3cd", relief="solid", bd=1)
        keys_frame.pack(fill=X, pady=(0, 20), padx=20)
        
        for i, key in enumerate(master_keys, 1):
            Label(keys_frame, text=f"{i}. {key}", font=("Courier", 9), 
                  bg="#fff3cd", fg="#856404", anchor="w").pack(fill=X, padx=10, pady=2)
        
        def copy_keys():
            keys_text = "\n".join([f"{i}. {key}" for i, key in enumerate(master_keys, 1)])
            setup_win.clipboard_clear()
            setup_win.clipboard_append(keys_text)
            messagebox.showinfo("Copied!", "Master keys copied to clipboard!")
        
        Button(content_area, text="📋 Copy Keys", command=copy_keys,
               font=("Segoe UI", 9), bg="#ffc107", fg="#212529", 
               relief="flat", padx=15, pady=5).pack(pady=(0, 20))
        
        def finish_setup():
            try:
                # Save all data
                save_secret_to_db(secret_key, user_email)
                save_master_keys(master_keys, user_email)
                
                messagebox.showinfo("🚀 Ready to Go!", 
                                   "AppLocker is now configured!\n\n"
                                   "You can now lock applications with authenticator protection.")
                
                setup_win.destroy()
                show_installed_apps()
                
            except Exception as e:
                messagebox.showerror("Setup Error", f"Failed to save setup: {str(e)}")
        
        # NAVIGATION BAR - fixed at bottom
        nav_bar = Frame(page_container, bg="#f8f9fa", height=70, relief="solid", bd=1)
        nav_bar.pack(fill=X, side=BOTTOM, pady=(10, 0))
        nav_bar.pack_propagate(False)
        
        # Center the buttons
        btn_container = Frame(nav_bar, bg="#f8f9fa")
        btn_container.place(relx=0.5, rely=0.5, anchor=CENTER)
        
        # Back button
        back_button = Button(btn_container, text="← BACK", 
                            command=lambda: prev_step(),
                            font=("Segoe UI", 12, "bold"), bg="#6c757d", fg="white",
                            relief="raised", padx=30, pady=10, bd=2)
        back_button.pack(side=LEFT, padx=10)
        
        # Complete button
        finish_button = Button(btn_container, text="COMPLETE SETUP 🚀", 
                           command=lambda: finish_setup(),
                           font=("Segoe UI", 12, "bold"), bg="#007bff", fg="white",
                           relief="raised", padx=30, pady=10, bd=2)
        finish_button.pack(side=LEFT, padx=10)
    
    # Navigation functions
    def next_step():
        nonlocal current_step
        
        # Validation for each step
        if current_step == 1:  # Email step
            if not hasattr(content_frame, 'validate_email') or not content_frame.validate_email():
                return
        elif current_step == 2:  # QR generation step
            if not hasattr(content_frame, 'secret_key') or not content_frame.secret_key():
                messagebox.showerror("Error", "Please generate QR code first!")
                return
        elif current_step == 3:  # Verification step
            if not hasattr(content_frame, 'verify_code') or not content_frame.verify_code():
                return
        
        if current_step < total_steps - 1:
            current_step += 1
            update_progress()
            show_current_step()
    
    def prev_step():
        nonlocal current_step
        if current_step > 0:
            current_step -= 1
            update_progress()
            show_current_step()
    
    def show_current_step():
        steps = [show_step_1_welcome, show_step_2_email, show_step_3_generate_qr, 
                show_step_4_verify, show_step_5_complete]
        steps[current_step]()
    
    # Global navigation variables - will be updated by show_current_step
    global_prev_btn = None
    global_next_btn = None
    
    # Initialize
    update_progress()
    show_current_step()
    
    setup_win.mainloop()

def show_existing_qr_code(user_email):
    """Show existing QR code for current user - no verification needed"""
    import os
    from app.auth import load_user_data
    
    try:
        # Get existing secret
        secret, email = load_user_data()
        if not secret or email != user_email:
            messagebox.showerror("Error", "No existing setup found. Please use 'Generate My QR Code' instead.")
            return
        
        # Show QR window
        qr_win = Tk()
        qr_win.title("Your Current QR Code")
        qr_win.geometry("500x650")
        qr_win.resizable(False, False)
        
        # Main frame
        main_frame = Frame(qr_win, padx=20, pady=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Title
        Label(main_frame, text="Your Current QR Code", 
              font=("Arial", 16, "bold")).pack(pady=(0, 10))
        
        Label(main_frame, text=f"Account: {email}", 
              font=("Arial", 12)).pack(pady=(0, 20))
        
        # Generate and display QR code
        try:
            qr_code_path = generate_qr_code(secret, email)
            
            if os.path.exists(qr_code_path):
                img = Image.open(qr_code_path)
                img = img.resize((300, 300), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                qr_label = Label(main_frame, image=photo, bg="white", relief="solid", borderwidth=2)
                qr_label.image = photo
                qr_label.pack(pady=20)
            else:
                Label(main_frame, text="QR Code generation failed", 
                      fg="red", font=("Arial", 12)).pack(pady=20)
        except Exception as e:
            log_error(f"Failed to display existing QR code: {e}")
            Label(main_frame, text="Error displaying QR code", 
                  fg="red", font=("Arial", 12)).pack(pady=20)
        
        # Manual entry
        Label(main_frame, text="Manual Entry Key:", 
              font=("Arial", 10, "bold")).pack(anchor=W, pady=(20, 5))
        
        key_entry = Entry(main_frame, font=("Courier", 10), width=50)
        key_entry.insert(0, secret)
        key_entry.config(state=DISABLED)
        key_entry.pack(fill=X, pady=(0, 10))
        
        # Copy button for the key
        def copy_key():
            qr_win.clipboard_clear()
            qr_win.clipboard_append(secret)
            messagebox.showinfo("Copied", "Secret key copied to clipboard!")
        
        Button(main_frame, text="Copy Key to Clipboard", command=copy_key,
               bg="lightblue", font=("Arial", 10)).pack(pady=5)
        
        # Instructions
        instructions = """
If you deleted AppLocker from Google Authenticator:
1. Open Google Authenticator app
2. Tap the + button to add a new account
3. Choose "Scan QR code" and scan the code above
   OR
4. Choose "Enter setup key" and paste the key below
5. AppLocker will appear in your authenticator

The 6-digit codes from your authenticator will work with AppLocker.
        """
        
        Label(main_frame, text=instructions, font=("Arial", 9), 
              justify=LEFT, bg="lightyellow", padx=10, pady=10).pack(fill=X, pady=10)
        
        # Close button
        Button(main_frame, text="Done", command=qr_win.destroy, 
               bg="lightgreen", font=("Arial", 12, "bold")).pack(pady=10)
        
        qr_win.mainloop()
        
    except Exception as e:
        log_error(f"Failed to show existing QR code: {e}")
        messagebox.showerror("Error", 
                           f"Failed to show QR code: {str(e)}\n\n"
                           f"Try using 'Generate My QR Code' to create a new one.")

def reset_app_completely():
    """Nuclear option: Reset everything without email verification"""
    import os
    
    result = messagebox.askyesno("⚠️ RESET EVERYTHING", 
                               "This will DELETE ALL AppLocker data:\n\n"
                               "✗ Your authenticator setup\n"
                               "✗ All locked apps\n"
                               "✗ All user data\n"
                               "✗ All settings\n\n"
                               "You will need to set up AppLocker from scratch.\n\n"
                               "Are you absolutely sure?")
    
    if not result:
        return
    
    # Double confirmation
    confirm = messagebox.askyesno("🔥 FINAL WARNING", 
                                "This action CANNOT be undone!\n\n"
                                "AppLocker will reset completely.\n\n"
                                "Continue with FULL RESET?")
    
    if not confirm:
        return
    
    try:
        from app.config import USER_DATA_FILE, LOCKED_APPS_FILE
        
        # Delete all data files
        files_to_delete = [
            USER_DATA_FILE,
            LOCKED_APPS_FILE,
            QR_CODE_FILE,
            os.path.join(os.path.dirname(__file__), "data", "reset_otps.json")
        ]
        
        deleted_files = []
        for file_path in files_to_delete:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
            except Exception as e:
                log_error(f"Failed to delete {file_path}: {e}")
        
        # Clear any remaining data directories
        try:
            data_dir = os.path.join(os.path.dirname(__file__), "data")
            if os.path.exists(data_dir):
                import shutil
                shutil.rmtree(data_dir)
        except Exception as e:
            log_error(f"Failed to clear data directory: {e}")
        
        log_event("AppLocker completely reset by user")
        
        messagebox.showinfo("✅ Reset Complete", 
                           f"AppLocker has been completely reset!\n\n"
                           f"Deleted: {', '.join(deleted_files) if deleted_files else 'No files found'}\n\n"
                           f"The app will now restart for fresh setup.")
        
        # Close current windows and restart setup
        import sys
        import subprocess
        
        # Start new instance
        subprocess.Popen([sys.executable] + sys.argv)
        
        # Exit current instance
        sys.exit(0)
        
    except Exception as e:
        log_error(f"Failed to reset app completely: {e}")
        messagebox.showerror("Reset Failed", 
                           f"Failed to reset completely: {str(e)}\n\n"
                           f"You may need to manually delete files in the app folder.")

def show_reset_authenticator_window(user_email):
    """Show window to reset authenticator with email OTP verification"""
    reset_win = Toplevel()
    reset_win.title("Reset Google Authenticator")
    reset_win.geometry("500x400")
    reset_win.resizable(False, False)
    reset_win.grab_set()  # Make modal
    
    # Main frame
    main_frame = Frame(reset_win, padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Title
    Label(main_frame, text="Reset Google Authenticator", 
          font=("Arial", 16, "bold")).pack(pady=(0, 20))
    
    # Info
    info_text = f"""Your registered email: {user_email}

We will send a One-Time Password (OTP) to your email.
This OTP will be valid for 15 minutes.

After verification, you can generate a new QR code."""
    
    Label(main_frame, text=info_text, font=("Arial", 10), 
          justify=LEFT, wraplength=450).pack(pady=(0, 20))
    
    # OTP entry (initially hidden)
    otp_frame = Frame(main_frame)
    otp_label = Label(otp_frame, text="Enter OTP from email:", font=("Arial", 10, "bold"))
    otp_entry = Entry(otp_frame, font=("Arial", 12), width=10, justify=CENTER)
    
    # Status label
    status_label = Label(main_frame, text="", font=("Arial", 10))
    status_label.pack(pady=10)
    
    def send_otp_email():
        """Send OTP to user's email"""
        try:
            # Clean up expired OTPs first
            cleanup_expired_otps()
            
            # Generate new OTP
            otp = generate_otp()
            
            # Save OTP
            if save_otp(user_email, otp):
                # Send email
                if send_reset_email(user_email, otp):
                    status_label.config(text="OTP sent to your email! Check your inbox.", fg="green")
                    
                    # Show OTP entry
                    otp_frame.pack(fill=X, pady=10)
                    otp_label.pack(anchor=W)
                    otp_entry.pack(fill=X, pady=5)
                    
                    # Hide send button, show verify button
                    send_btn.pack_forget()
                    verify_btn.pack(pady=10)
                    
                    log_event(f"Reset OTP sent to {user_email}")
                else:
                    status_label.config(text="Failed to send email. Check email configuration.", fg="red")
            else:
                status_label.config(text="Failed to generate OTP. Please try again.", fg="red")
                
        except Exception as e:
            log_error(f"Failed to send reset OTP: {e}")
            status_label.config(text="Error sending OTP. Please try again.", fg="red")
    
    def verify_and_reset():
        """Verify OTP and proceed to reset"""
        entered_otp = otp_entry.get().strip()
        if not entered_otp:
            status_label.config(text="Please enter the OTP from your email.", fg="red")
            return
        
        if verify_otp(user_email, entered_otp):
            status_label.config(text="OTP verified! Generating new QR code...", fg="green")
            reset_win.after(1000, lambda: complete_reset(user_email, reset_win))
        else:
            status_label.config(text="Invalid or expired OTP. Please try again.", fg="red")
    
    def complete_reset(email, window):
        """Complete the reset process with new QR code"""
        try:
            # Generate new secret
            new_secret = generate_secret_key()
            
            # Save new secret
            save_secret_to_db(new_secret, email)
            
            # Close reset window
            window.destroy()
            
            # Show success and new QR
            messagebox.showinfo("Reset Complete", 
                               f"Authenticator reset successful!\n"
                               f"A new QR code will be generated for {email}")
            
            # Show setup window with new QR
            show_new_qr_setup(email, new_secret)
            
        except Exception as e:
            log_error(f"Failed to complete reset: {e}")
            messagebox.showerror("Reset Failed", "Failed to complete reset. Please try again.")
    
    # Buttons
    send_btn = Button(main_frame, text="Send OTP to Email", 
                     command=send_otp_email, bg="lightblue", 
                     font=("Arial", 12, "bold"), pady=5)
    send_btn.pack(pady=10)
    
    verify_btn = Button(main_frame, text="Verify OTP & Reset", 
                       command=verify_and_reset, bg="lightgreen", 
                       font=("Arial", 12, "bold"), pady=5)
    
    # Close button
    Button(main_frame, text="Cancel", command=reset_win.destroy, 
           bg="lightgray", font=("Arial", 10)).pack(side=BOTTOM, pady=20)

def show_new_qr_setup(email, secret):
    """Show QR code setup window after reset"""
    import os  # Import os here for file checking
    
    qr_win = Tk()
    qr_win.title("New QR Code - Scan with Authenticator")
    qr_win.geometry("500x600")
    
    # Main frame
    main_frame = Frame(qr_win, padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Title
    Label(main_frame, text="New QR Code Generated", 
          font=("Arial", 16, "bold")).pack(pady=(0, 10))
    
    Label(main_frame, text=f"Account: {email}", 
          font=("Arial", 12)).pack(pady=(0, 20))
    
    # Generate and display QR code
    try:
        qr_code_path = generate_qr_code(secret, email)
        
        if os.path.exists(qr_code_path):
            img = Image.open(qr_code_path)
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            qr_label = Label(main_frame, image=photo, bg="white")
            qr_label.image = photo
            qr_label.pack(pady=20)
        else:
            Label(main_frame, text="QR Code generation failed", 
                  fg="red", font=("Arial", 12)).pack(pady=20)
    except Exception as e:
        log_error(f"Failed to display new QR code: {e}")
        Label(main_frame, text="Error displaying QR code", 
              fg="red", font=("Arial", 12)).pack(pady=20)
    
    # Manual entry
    Label(main_frame, text="Manual Entry Key:", 
          font=("Arial", 10, "bold")).pack(anchor=W, pady=(20, 5))
    
    key_entry = Entry(main_frame, font=("Courier", 10), width=50)
    key_entry.insert(0, secret)
    key_entry.config(state=DISABLED)
    key_entry.pack(fill=X, pady=(0, 20))
    
    # Instructions
    instructions = """
1. Delete the old AppLocker entry from Google Authenticator
2. Scan this new QR code or enter the key manually
3. The new 6-digit codes will work with AppLocker
4. Close this window when done
    """
    
    Label(main_frame, text=instructions, font=("Arial", 10), 
          justify=LEFT, bg="lightyellow", padx=10, pady=10).pack(fill=X, pady=10)
    
    Button(main_frame, text="Done", command=qr_win.destroy, 
           bg="lightgreen", font=("Arial", 12, "bold")).pack(pady=20)
    
    qr_win.mainloop()

def show_installed_apps():
    """Show apps list with modern UI design"""
    apps = get_installed_apps()  # Get the list of installed apps
    if not apps:
        messagebox.showerror("Error", "No apps found.")
        return

    # Display apps in a new window
    apps_win = Tk()
    apps_win.title("Lock Applications")
    apps_win.geometry("800x600")
    apps_win.configure(bg="#f8f9fa")
    apps_win.resizable(True, True)
    
    # Center window
    apps_win.update_idletasks()
    x = (apps_win.winfo_screenwidth() // 2) - (800 // 2)
    y = (apps_win.winfo_screenheight() // 2) - (600 // 2)
    apps_win.geometry(f"800x600+{x}+{y}")

    # Header
    header_frame = Frame(apps_win, bg="#28a745", height=80)
    header_frame.pack(fill=X)
    header_frame.pack_propagate(False)
    
    Label(header_frame, text=f"🔒 Lock Applications", 
          font=("Segoe UI", 16, "bold"), fg="white", bg="#28a745").pack(pady=20)
    
    Label(header_frame, text=f"Found {len(apps)} installed applications", 
          font=("Segoe UI", 10), fg="#d4edda", bg="#28a745").pack(pady=(0, 10))
    
    # Main content
    main_frame = Frame(apps_win, bg="#f8f9fa", padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Search frame
    search_frame = Frame(main_frame, bg="#f8f9fa")
    search_frame.pack(fill=X, pady=(0, 15))
    
    Label(search_frame, text="🔍 Search Applications:", 
          font=("Segoe UI", 11, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(side=LEFT)
    
    search_var = StringVar()
    search_entry = Entry(search_frame, textvariable=search_var, font=("Segoe UI", 11), 
                        width=30, relief="solid", bd=1)
    search_entry.pack(side=LEFT, padx=(10, 0), ipady=5)
    
    # Clear search button
    def clear_search():
        search_var.set("")
        populate_listbox()
    
    Button(search_frame, text="❌", command=clear_search,
           font=("Segoe UI", 8), bg="#dc3545", fg="white", 
           relief="flat", padx=5, pady=2).pack(side=LEFT, padx=(5, 0))
    
    # Apps list frame
    list_frame = Frame(main_frame, bg="white", relief="solid", bd=1)
    list_frame.pack(fill=BOTH, expand=True, pady=(0, 15))

    # Add scrollbars to the listbox
    v_scrollbar = Scrollbar(list_frame, orient=VERTICAL)
    h_scrollbar = Scrollbar(list_frame, orient=HORIZONTAL)
    
    listbox = Listbox(list_frame, 
                     font=("Segoe UI", 10),
                     yscrollcommand=v_scrollbar.set,
                     xscrollcommand=h_scrollbar.set,
                     selectmode=SINGLE,
                     bg="white", fg="#2c3e50", 
                     selectbackground="#007bff",
                     selectforeground="white",
                     relief="flat", bd=0)
    
    # Status frame - MOVED BEFORE populate_listbox function
    status_frame = Frame(main_frame, bg="#f8f9fa")
    status_frame.pack(fill=X, pady=(0, 15))
    
    count_label = Label(status_frame, text="", font=("Segoe UI", 9), 
                       bg="#f8f9fa", fg="#6c757d")
    count_label.pack(side=LEFT)
    
    def populate_listbox():
        search_query = search_var.get().lower()
        listbox.delete(0, END)
        
        filtered_apps = []
        for app in sorted(apps):
            if search_query in app.lower():
                filtered_apps.append(app)
        
        for app in filtered_apps:
            listbox.insert(END, f"📱 {app}")
        
        # Update count
        count_label.config(text=f"Showing {len(filtered_apps)} of {len(apps)} applications")
    
    # Populate initially
    populate_listbox()
    
    # Configure scrollbars
    v_scrollbar.config(command=listbox.yview)
    h_scrollbar.config(command=listbox.xview)
    
    # Pack scrollbars and listbox with padding
    listbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    v_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
    h_scrollbar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
    
    # Configure grid weights
    list_frame.grid_rowconfigure(0, weight=1)
    list_frame.grid_columnconfigure(0, weight=1)
    
    # Bind search
    search_var.trace("w", lambda *args: populate_listbox())
    
    # Selected app info
    selected_label = Label(status_frame, text="Select an app to lock", 
                          font=("Segoe UI", 9), bg="#f8f9fa", fg="#6c757d")
    selected_label.pack(side=RIGHT)
    
    def on_select(event):
        selection = listbox.curselection()
        if selection:
            app_name = listbox.get(selection[0]).replace("📱 ", "")
            selected_label.config(text=f"Selected: {app_name}")
        else:
            selected_label.config(text="Select an app to lock")
    
    listbox.bind('<<ListboxSelect>>', on_select)

    # Buttons frame
    btn_frame = Frame(main_frame, bg="#f8f9fa")
    btn_frame.pack(fill=X, pady=10)
    
    # Left side buttons
    left_buttons = Frame(btn_frame, bg="#f8f9fa")
    left_buttons.pack(side=LEFT)

    def lock_selected_app():
        selection = listbox.curselection()
        if selection:
            app_name = listbox.get(selection[0]).replace("📱 ", "")
            lock_app_with_confirmation(app_name, apps_win)
        else:
            messagebox.showwarning("No Selection", "Please select an application to lock.")
    
    Button(left_buttons, text="🔒 Lock Selected App", command=lock_selected_app,
           font=("Segoe UI", 11, "bold"), bg="#dc3545", fg="white", 
           relief="flat", padx=25, pady=10).pack(side=LEFT, padx=(0, 15))
           
    Button(left_buttons, text="🔄 Refresh List", 
           command=lambda: refresh_and_update_list(listbox, apps_win),
           font=("Segoe UI", 10), bg="#17a2b8", fg="white", 
           relief="flat", padx=20, pady=10).pack(side=LEFT, padx=(0, 15))
    
    # Right side buttons
    right_buttons = Frame(btn_frame, bg="#f8f9fa")
    right_buttons.pack(side=RIGHT)
           
    Button(right_buttons, text="🏠 Back to Main", 
           command=lambda: [apps_win.destroy(), show_unlock_interface()],
           font=("Segoe UI", 10), bg="#6c757d", fg="white", 
           relief="flat", padx=20, pady=10).pack(side=RIGHT)

def refresh_and_update_list(listbox, parent_window):
    """Refresh the app list with loading indicator"""
    
    # Show loading
    listbox.delete(0, END)
    listbox.insert(0, "🔄 Refreshing applications...")
    parent_window.update()
    
    try:
        apps = get_installed_apps()
        listbox.delete(0, END)
        
        for app in sorted(apps):
            listbox.insert(END, f"📱 {app}")
        
        messagebox.showinfo("Refreshed", f"Found {len(apps)} applications")
        
    except Exception as e:
        listbox.delete(0, END)
        listbox.insert(0, "❌ Failed to refresh applications")
        messagebox.showerror("Refresh Failed", f"Failed to refresh: {str(e)}")

def lock_app_with_confirmation(app_name, parent_window):
    """Lock app with modern confirmation dialog"""
    
    # Create confirmation dialog
    confirm_win = Toplevel(parent_window)
    confirm_win.title("Confirm App Lock")
    confirm_win.geometry("450x300")
    confirm_win.configure(bg="white")
    confirm_win.resizable(False, False)
    confirm_win.grab_set()
    
    # Center dialog
    confirm_win.update_idletasks()
    x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - 225
    y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - 150
    confirm_win.geometry(f"450x300+{x}+{y}")
    
    # Header
    header_frame = Frame(confirm_win, bg="#dc3545", height=60)
    header_frame.pack(fill=X)
    header_frame.pack_propagate(False)
    
    Label(header_frame, text="🔒 Lock Application", 
          font=("Segoe UI", 14, "bold"), fg="white", bg="#dc3545").pack(pady=15)
    
    # Content
    content_frame = Frame(confirm_win, bg="white", padx=30, pady=20)
    content_frame.pack(fill=BOTH, expand=True)
    
    Label(content_frame, text=f"Lock '{app_name}' with Google Authenticator?", 
          font=("Segoe UI", 12, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 15))
    
    info_text = """After locking, you'll need to enter:
• 6-digit code from Google Authenticator
• OR 16-character master backup key

The app will be blocked immediately when launched."""
    
    Label(content_frame, text=info_text, font=("Segoe UI", 10), 
          bg="white", fg="#6c757d", justify=LEFT).pack(pady=(0, 20))
    
    def confirm_lock():
        try:
            # Load existing locked apps
            try:
                with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
                    locked_apps = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                locked_apps = {}

            locked_apps[app_name] = True  # Mark as locked

            # Ensure directory exists
            os.makedirs(os.path.dirname(LOCKED_APPS_FILE), exist_ok=True)
            
            with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                json.dump(locked_apps, file, indent=2)

            log_event(f"App '{app_name}' is now locked")
            
            confirm_win.destroy()
            
            messagebox.showinfo("App Locked!", 
                               f"✅ '{app_name}' is now protected!\n\n"
                               f"🔒 It will require authentication to open\n"
                               f"🛡️ Protection is active immediately")
            
            parent_window.destroy()
            show_unlock_interface()
            
        except Exception as e:
            log_error(f"Failed to lock app: {e}")
            messagebox.showerror("Lock Failed", f"Failed to lock '{app_name}': {str(e)}")
    
    # Buttons
    buttons_frame = Frame(content_frame, bg="white")
    buttons_frame.pack(side=BOTTOM, pady=20)
    
    Button(buttons_frame, text="🔒 Yes, Lock App", command=confirm_lock,
           font=("Segoe UI", 11, "bold"), bg="#dc3545", fg="white", 
           relief="flat", padx=25, pady=10).pack(side=LEFT, padx=(0, 15))
    
    Button(buttons_frame, text="Cancel", command=confirm_win.destroy,
           font=("Segoe UI", 10), bg="#6c757d", fg="white", 
           relief="flat", padx=20, pady=10).pack(side=LEFT)

def show_unlock_interface():
    """Show the main unlock interface - NEW MODERN DESIGN"""
    unlock_win = Tk()
    unlock_win.title(WINDOW_TITLE)
    unlock_win.geometry("700x500")
    unlock_win.configure(bg="#f8f9fa")
    unlock_win.resizable(False, False)
    
    # Center window
    unlock_win.update_idletasks()
    x = (unlock_win.winfo_screenwidth() // 2) - (700 // 2)
    y = (unlock_win.winfo_screenheight() // 2) - (500 // 2)
    unlock_win.geometry(f"700x500+{x}+{y}")
    
    # Load locked apps
    try:
        with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
            locked_apps = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        locked_apps = {}
    
    # Session management
    session_active = getattr(show_unlock_interface, 'session_active', False)
    
    # Header
    header_frame = Frame(unlock_win, bg="#343a40", height=80)
    header_frame.pack(fill=X)
    header_frame.pack_propagate(False)
    
    # App title and session status
    title_frame = Frame(header_frame, bg="#343a40")
    title_frame.pack(fill=X, padx=20, pady=15)
    
    Label(title_frame, text="🔐 AppLocker", font=("Segoe UI", 18, "bold"), 
          fg="white", bg="#343a40").pack(side=LEFT)
    
    # Session indicator
    session_color = "#28a745" if session_active else "#dc3545"
    session_text = "🟢 Unlocked Session" if session_active else "🔴 Locked Session"
    
    session_label = Label(title_frame, text=session_text, 
                         font=("Segoe UI", 10), fg=session_color, bg="#343a40")
    session_label.pack(side=RIGHT)
    
    # Main content area
    content_frame = Frame(unlock_win, bg="#f8f9fa", padx=20, pady=20)
    content_frame.pack(fill=BOTH, expand=True)
    
    if not locked_apps:
        # No apps locked
        empty_frame = Frame(content_frame, bg="white", relief="solid", bd=1)
        empty_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        Label(empty_frame, text="📱", font=("Segoe UI", 48), bg="white").pack(pady=(40, 20))
        Label(empty_frame, text="No Applications Locked", 
              font=("Segoe UI", 16, "bold"), bg="white", fg="#6c757d").pack()
        Label(empty_frame, text="Click 'Lock New Apps' to get started", 
              font=("Segoe UI", 11), bg="white", fg="#adb5bd").pack(pady=(10, 40))
        
        Button(empty_frame, text="🔒 Lock New Apps", 
               command=lambda: [unlock_win.destroy(), show_installed_apps()],
               font=("Segoe UI", 12, "bold"), bg="#007bff", fg="white", 
               relief="flat", padx=25, pady=10).pack(pady=20)
    else:
        # Apps list header
        list_header = Frame(content_frame, bg="#f8f9fa")
        list_header.pack(fill=X, pady=(0, 15))
        
        Label(list_header, text=f"🔒 Locked Applications ({len(locked_apps)})", 
              font=("Segoe UI", 14, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(side=LEFT)
        
        if session_active:
            def lock_session():
                show_unlock_interface.session_active = False
                unlock_win.destroy()
                show_unlock_interface()
            
            Button(list_header, text="🔒 Lock Session", command=lock_session,
                   font=("Segoe UI", 9), bg="#ffc107", fg="#212529", 
                   relief="flat", padx=15, pady=5).pack(side=RIGHT)
        
        # Apps list with modern styling
        list_frame = Frame(content_frame, bg="white", relief="solid", bd=1)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 15))
        
        # Scrollable listbox
        scrollbar = Scrollbar(list_frame, orient=VERTICAL)
        listbox = Listbox(list_frame, font=("Segoe UI", 11), 
                         yscrollcommand=scrollbar.set, selectmode=SINGLE,
                         bg="white", fg="#2c3e50", selectbackground="#007bff",
                         selectforeground="white", relief="flat", bd=0)
        
        for app in sorted(locked_apps.keys()):
            listbox.insert(END, f"🔒 {app}")
        
        listbox.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y, padx=(0, 10), pady=10)
        
        def unlock_selected():
            selection = listbox.curselection()
            if selection:
                app_name = listbox.get(selection[0]).replace("🔒 ", "")
                unlock_app_with_popup(app_name, unlock_win)
        
        def remove_lock():
            selection = listbox.curselection()
            if selection:
                app_name = listbox.get(selection[0]).replace("🔒 ", "")
                result = messagebox.askyesno("Remove Lock", 
                                           f"Remove protection from '{app_name}'?\n\n"
                                           f"The app will no longer require authentication.")
                if result:
                    del locked_apps[app_name]
                    with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                        json.dump(locked_apps, file, indent=2)
                    listbox.delete(selection[0])
                    log_event(f"Lock removed from app: {app_name}")
                    
                    # Refresh if no apps left
                    if not locked_apps:
                        unlock_win.destroy()
                        show_unlock_interface()
    
    # Action buttons
    buttons_frame = Frame(content_frame, bg="#f8f9fa")
    buttons_frame.pack(fill=X, pady=10)
    
    # Left side buttons
    left_buttons = Frame(buttons_frame, bg="#f8f9fa")
    left_buttons.pack(side=LEFT)
    
    if locked_apps:
        Button(left_buttons, text="🔓 Unlock App", command=unlock_selected,
               font=("Segoe UI", 10, "bold"), bg="#28a745", fg="white", 
               relief="flat", padx=20, pady=8).pack(side=LEFT, padx=(0, 10))
        
        Button(left_buttons, text="🗑️ Remove Lock", command=remove_lock,
               font=("Segoe UI", 10), bg="#dc3545", fg="white", 
               relief="flat", padx=20, pady=8).pack(side=LEFT, padx=(0, 10))
    
    Button(left_buttons, text="🔒 Lock New Apps", 
           command=lambda: [unlock_win.destroy(), show_installed_apps()],
           font=("Segoe UI", 10), bg="#007bff", fg="white", 
           relief="flat", padx=20, pady=8).pack(side=LEFT, padx=(0, 10))
    
    # Right side buttons
    right_buttons = Frame(buttons_frame, bg="#f8f9fa")
    right_buttons.pack(side=RIGHT)
    
    Button(right_buttons, text="📱 My QR Code", 
           command=lambda: show_my_qr_from_main(),
           font=("Segoe UI", 10), bg="#17a2b8", fg="white", 
           relief="flat", padx=15, pady=8).pack(side=RIGHT, padx=(10, 0))
    
    Button(right_buttons, text="⚙️ Settings", 
           command=lambda: show_settings_window(unlock_win),
           font=("Segoe UI", 10), bg="#6c757d", fg="white", 
           relief="flat", padx=15, pady=8).pack(side=RIGHT, padx=(10, 0))
    
    Button(right_buttons, text="❌ Exit", command=unlock_win.destroy,
           font=("Segoe UI", 10), bg="#adb5bd", fg="white", 
           relief="flat", padx=15, pady=8).pack(side=RIGHT, padx=(10, 0))
    
    unlock_win.mainloop()

def unlock_app_with_popup(app_name, parent_window):
    """Show modern unlock popup with PIN/master key input"""
    
    # Check if session is active
    if getattr(show_unlock_interface, 'session_active', False):
        # Session is active, unlock directly
        try:
            unlock_app(app_name)
            return
        except Exception as e:
            messagebox.showerror("Unlock Failed", f"Failed to unlock {app_name}: {str(e)}")
            return
    
    # Create popup window
    popup = Toplevel(parent_window)
    popup.title(f"Unlock {app_name}")
    popup.geometry("400x350")
    popup.configure(bg="white")
    popup.resizable(False, False)
    popup.grab_set()  # Make modal
    
    # Center popup
    popup.update_idletasks()
    x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - 200
    y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - 175
    popup.geometry(f"400x350+{x}+{y}")
    
    # Header
    header_frame = Frame(popup, bg="#007bff", height=60)
    header_frame.pack(fill=X)
    header_frame.pack_propagate(False)
    
    Label(header_frame, text=f"🔓 Unlock {app_name}", 
          font=("Segoe UI", 14, "bold"), fg="white", bg="#007bff").pack(pady=15)
    
    # Content
    content_frame = Frame(popup, bg="white", padx=30, pady=20)
    content_frame.pack(fill=BOTH, expand=True)
    
    Label(content_frame, text="Enter your authentication code:", 
          font=("Segoe UI", 11, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 15))
    
    # Code input
    code_var = StringVar()
    code_entry = Entry(content_frame, textvariable=code_var, font=("Segoe UI", 14, "bold"), 
                      width=15, justify=CENTER, relief="solid", bd=2)
    code_entry.pack(pady=(0, 10), ipady=8)
    code_entry.focus()
    
    # Feedback label
    feedback_label = Label(content_frame, text="", font=("Segoe UI", 10), bg="white")
    feedback_label.pack(pady=(0, 15))
    
    def verify_and_unlock():
        code = code_var.get().strip()
        
        if not code:
            feedback_label.config(text="Please enter a code", fg="#dc3545")
            return
        
        # Get user data
        try:
            from app.auth import load_user_data
            secret, email = load_user_data()
            
            if not secret or not email:
                feedback_label.config(text="User data not found", fg="#dc3545")
                return
            
            success = False
            
            # Try TOTP verification
            if len(code) == 6 and code.isdigit():
                try:
                    import pyotp
                    totp = pyotp.TOTP(secret)
                    if totp.verify(code, valid_window=2):
                        success = True
                        feedback_label.config(text="✅ Authenticator code verified!", fg="#28a745")
                except Exception as e:
                    log_error(f"TOTP verification failed: {e}")
            
            # Try master key verification
            if not success and len(code) == 16:
                if verify_master_key(code, email):
                    success = True
                    feedback_label.config(text="✅ Master key verified!", fg="#28a745")
                else:
                    feedback_label.config(text="❌ Invalid or used master key", fg="#dc3545")
            
            if not success and len(code) == 6:
                feedback_label.config(text="❌ Invalid authenticator code", fg="#dc3545")
            elif not success:
                feedback_label.config(text="❌ Invalid code format", fg="#dc3545")
            
            if success:
                popup.update()
                popup.after(1000, lambda: [popup.destroy(), unlock_app_success(app_name, parent_window)])
                
        except Exception as e:
            feedback_label.config(text="❌ Verification error", fg="#dc3545")
            log_error(f"Unlock verification error: {e}")
    
    # Unlock button
    Button(content_frame, text="🔓 Unlock App", command=verify_and_unlock,
           font=("Segoe UI", 11, "bold"), bg="#28a745", fg="white", 
           relief="flat", padx=25, pady=10).pack(pady=(0, 15))
    
    # Session unlock option
    def unlock_session():
        code = code_var.get().strip()
        
        if not code:
            feedback_label.config(text="Please enter a code first", fg="#dc3545")
            return
        
        # Verify code first
        try:
            from app.auth import load_user_data
            secret, email = load_user_data()
            
            success = False
            
            # Try TOTP verification
            if len(code) == 6 and code.isdigit():
                try:
                    import pyotp
                    totp = pyotp.TOTP(secret)
                    if totp.verify(code, valid_window=2):
                        success = True
                except Exception as e:
                    log_error(f"TOTP verification failed: {e}")
            
            # Try master key verification
            if not success and len(code) == 16:
                if verify_master_key(code, email):
                    success = True
            
            if success:
                # Activate session
                show_unlock_interface.session_active = True
                feedback_label.config(text="✅ Session unlocked!", fg="#28a745")
                popup.update()
                popup.after(1000, lambda: [popup.destroy(), unlock_app_success(app_name, parent_window, refresh_main=True)])
            else:
                feedback_label.config(text="❌ Invalid code", fg="#dc3545")
                
        except Exception as e:
            feedback_label.config(text="❌ Session unlock failed", fg="#dc3545")
            log_error(f"Session unlock error: {e}")
    
    Button(content_frame, text="🔓 Unlock Session (All Apps)", command=unlock_session,
           font=("Segoe UI", 10), bg="#ffc107", fg="#212529", 
           relief="flat", padx=20, pady=8).pack(pady=(0, 10))
    
    # Help text
    help_text = """6-digit code: Google Authenticator
16-character code: Master backup key

Session unlock allows access to all locked apps
until you manually lock the session again."""
    
    Label(content_frame, text=help_text, font=("Segoe UI", 8), 
          bg="white", fg="#6c757d", justify=LEFT).pack(pady=(10, 0))
    
    # Cancel button
    Button(content_frame, text="Cancel", command=popup.destroy,
           font=("Segoe UI", 10), bg="#6c757d", fg="white", 
           relief="flat", padx=20, pady=5).pack(side=BOTTOM, pady=(10, 0))
    
    # Bind Enter key
    popup.bind('<Return>', lambda e: verify_and_unlock())
    
    popup.mainloop()

def unlock_app_success(app_name, parent_window, refresh_main=False):
    """Handle successful app unlock"""
    try:
        unlock_app(app_name)
        
        if refresh_main:
            # Refresh main window to show session status
            parent_window.destroy()
            show_unlock_interface()
        else:
            messagebox.showinfo("Unlocked!", f"✅ {app_name} has been unlocked!")
            
    except Exception as e:
        messagebox.showerror("Unlock Failed", f"Failed to unlock {app_name}: {str(e)}")

def show_settings_window(parent):
    """Show settings window with app management options"""
    settings = Toplevel(parent)
    settings.title("AppLocker Settings")
    settings.geometry("500x400")
    settings.configure(bg="white")
    settings.resizable(False, False)
    settings.grab_set()
    
    # Center window
    settings.update_idletasks()
    x = parent.winfo_x() + 100
    y = parent.winfo_y() + 50
    settings.geometry(f"500x400+{x}+{y}")
    
    # Header
    header_frame = Frame(settings, bg="#343a40", height=60)
    header_frame.pack(fill=X)
    header_frame.pack_propagate(False)
    
    Label(header_frame, text="⚙️ AppLocker Settings", 
          font=("Segoe UI", 14, "bold"), fg="white", bg="#343a40").pack(pady=15)
    
    # Content
    content_frame = Frame(settings, bg="white", padx=30, pady=20)
    content_frame.pack(fill=BOTH, expand=True)
    
    # Get user info
    try:
        from app.auth import load_user_data
        secret, email = load_user_data()
    except:
        email = "Unknown"
    
    # User info
    Label(content_frame, text=f"👤 Account: {email}", 
          font=("Segoe UI", 12, "bold"), bg="white", fg="#2c3e50").pack(pady=(0, 20))
    
    # Options
    Button(content_frame, text="📱 Show My QR Code", 
           command=lambda: [settings.destroy(), show_my_qr_from_main()],
           font=("Segoe UI", 11), bg="#17a2b8", fg="white", 
           relief="flat", padx=25, pady=10, width=25).pack(pady=5)
    
    Button(content_frame, text="🔑 View Master Keys", 
           command=lambda: show_master_keys_window(settings, email),
           font=("Segoe UI", 11), bg="#ffc107", fg="#212529", 
           relief="flat", padx=25, pady=10, width=25).pack(pady=5)
    
    Button(content_frame, text="🔄 Reset Authenticator", 
           command=lambda: [settings.destroy(), show_reset_authenticator_window(email)],
           font=("Segoe UI", 11), bg="#fd7e14", fg="white", 
           relief="flat", padx=25, pady=10, width=25).pack(pady=5)
    
    Button(content_frame, text="🔥 Reset Everything", 
           command=lambda: [settings.destroy(), reset_app_completely()],
           font=("Segoe UI", 11), bg="#dc3545", fg="white", 
           relief="flat", padx=25, pady=10, width=25).pack(pady=5)
    
    # Session info
    session_status = "Active" if getattr(show_unlock_interface, 'session_active', False) else "Locked"
    Label(content_frame, text=f"🔒 Session Status: {session_status}", 
          font=("Segoe UI", 10), bg="white", fg="#6c757d").pack(pady=(30, 0))
    
    Button(content_frame, text="Close", command=settings.destroy,
           font=("Segoe UI", 10), bg="#6c757d", fg="white", 
           relief="flat", padx=20, pady=5).pack(side=BOTTOM, pady=(20, 0))

def show_master_keys_window(parent, email):
    """Show master keys window"""
    try:
        from app.config import USER_DATA_FILE
        import json
        
        master_keys_file = USER_DATA_FILE.replace("user_data.txt", "master_keys.json")
        
        if not os.path.exists(master_keys_file):
            messagebox.showinfo("No Keys", "No master keys found. They may have been generated in an older version.")
            return
        
        with open(master_keys_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        keys = data.get("keys", [])
        used_keys = data.get("used_keys", [])
        
        # Create window
        keys_win = Toplevel(parent)
        keys_win.title("Master Backup Keys")
        keys_win.geometry("600x500")
        keys_win.configure(bg="white")
        keys_win.grab_set()
        
        # Header
        header_frame = Frame(keys_win, bg="#ffc107", height=60)
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False)
        
        Label(header_frame, text="🔑 Master Backup Keys", 
              font=("Segoe UI", 14, "bold"), fg="#212529", bg="#ffc107").pack(pady=15)
        
        # Content
        content_frame = Frame(keys_win, bg="white", padx=30, pady=20)
        content_frame.pack(fill=BOTH, expand=True)
        
        Label(content_frame, text="⚠️ Keep these keys safe! Each key can only be used once.", 
              font=("Segoe UI", 10, "bold"), bg="white", fg="#dc3545").pack(pady=(0, 20))
        
        # Keys display
        keys_frame = Frame(content_frame, bg="#f8f9fa", relief="solid", bd=1)
        keys_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        for i, key in enumerate(keys, 1):
            is_used = key in used_keys
            color = "#dc3545" if is_used else "#28a745"
            status = "USED" if is_used else "AVAILABLE"
            
            key_frame = Frame(keys_frame, bg="#f8f9fa")
            key_frame.pack(fill=X, padx=10, pady=5)
            
            Label(key_frame, text=f"{i}.", font=("Segoe UI", 10, "bold"), 
                  bg="#f8f9fa", fg="#2c3e50").pack(side=LEFT)
            
            Label(key_frame, text=key, font=("Courier", 10), 
                  bg="#f8f9fa", fg=color).pack(side=LEFT, padx=(10, 0))
            
            Label(key_frame, text=status, font=("Segoe UI", 8, "bold"), 
                  bg="#f8f9fa", fg=color).pack(side=RIGHT)
        
        def copy_available_keys():
            available = [key for key in keys if key not in used_keys]
            if available:
                keys_text = "\n".join([f"{i}. {key}" for i, key in enumerate(available, 1)])
                keys_win.clipboard_clear()
                keys_win.clipboard_append(keys_text)
                messagebox.showinfo("Copied!", f"Copied {len(available)} available keys to clipboard!")
            else:
                messagebox.showwarning("No Keys", "No available keys to copy.")
        
        Button(content_frame, text="📋 Copy Available Keys", command=copy_available_keys,
               font=("Segoe UI", 10), bg="#007bff", fg="white", 
               relief="flat", padx=20, pady=8).pack(side=LEFT)
        
        Button(content_frame, text="Close", command=keys_win.destroy,
               font=("Segoe UI", 10), bg="#6c757d", fg="white", 
               relief="flat", padx=20, pady=8).pack(side=RIGHT)
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load master keys: {str(e)}")

def show_my_qr_from_main():
    """Show QR code from main interface"""
    user_email = get_user_email_from_storage()
    if user_email:
        show_existing_qr_code(user_email)
    else:
        messagebox.showerror("Error", "No user setup found. Please restart AppLocker to set up.")

import json
import pyotp
import qrcode
import os
import sys
import subprocess
import shutil
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

# Function to generate a QR Code for Google Authenticator setup
def generate_qr_code(secret, email):
    try:
        # Ensure assets directory exists
        import os
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

# Function to handle user setup for 2FA authentication only
def user_setup():
    setup_win = Tk()
    setup_win.title(f"{WINDOW_TITLE} - Setup")
    setup_win.geometry("600x900")  # Made even taller to ensure all elements are visible
    setup_win.resizable(True, True)  # Allow resizing
    
    # Create a canvas and scrollbar for scrolling
    canvas = Canvas(setup_win)
    scrollbar = Scrollbar(setup_win, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Pack the canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Add mouse wheel scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind("<MouseWheel>", on_mousewheel)
    
    # Main frame (now inside the scrollable frame)
    main_frame = Frame(scrollable_frame, padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Title with progress indicator
    title_label = Label(main_frame, text="AppLocker Setup - Step 1 of 4", 
                       font=("Arial", 16, "bold"))
    title_label.pack(pady=(0, 10))
    
    # Progress bar visual
    progress_frame = Frame(main_frame)
    progress_frame.pack(fill=X, pady=(0, 20))
    
    # Variables for QR code and progress tracking
    secret_key = None
    qr_label = None
    secret_entry = None
    progress_labels = []
    steps = ["Enter Email", "Generate QR", "Scan Code", "Complete"]
    
    def update_progress(step):
        """Update the progress indicator"""
        for i, label in enumerate(progress_labels):
            if i <= step:
                label.config(bg="lightgreen")
            else:
                label.config(bg="lightgray")
        
        step_names = ["Enter Email", "Generate QR", "Scan Code", "Complete"]
        title_label.config(text=f"AppLocker Setup - Step {step+1} of 4: {step_names[step]}")
    
    # Store progress labels for updates
    for i, step in enumerate(steps):
        color = "lightgreen" if i == 0 else "lightgray"
        step_label = Label(progress_frame, text=f"{i+1}. {step}", 
                          bg=color, font=("Arial", 9), padx=10, pady=5)
        step_label.pack(side=LEFT, padx=2, fill=X, expand=True)
        progress_labels.append(step_label)

    # User identification frame
    user_frame = Frame(main_frame)
    user_frame.pack(fill=X, pady=(0, 20))
    
    Label(user_frame, text="Enter your name/email (for identification):", font=("Arial", 10, "bold")).pack(anchor=W)
    user_entry = Entry(user_frame, font=("Arial", 12), width=40)
    user_entry.pack(fill=X, pady=5)
    user_entry.insert(0, "user@example.com")
    
    # Bind email entry to update progress
    def on_email_change(*args):
        if user_entry.get().strip():
            update_progress(1)
        else:
            update_progress(0)
    
    user_entry.bind('<KeyRelease>', on_email_change)

    # Instructions with better formatting
    instructions = """
📋 SETUP INSTRUCTIONS:

1️⃣ Enter your name/email above (for account identification)
2️⃣ Install Google Authenticator app on your phone  
3️⃣ Click 'Generate My QR Code' button below
4️⃣ Scan the QR code with Google Authenticator
5️⃣ Click '✅ Complete Setup' to finish

🔄 Lost your QR code? Use the recovery buttons below!
📧 Each user gets their own unique setup!
🔒 Your apps will be protected with 6-digit codes from the authenticator!
    """
    
    instructions_frame = Frame(main_frame, bg="lightyellow", relief="solid", bd=2)
    instructions_frame.pack(fill=X, pady=(0, 20))
    
    instructions_label = Label(instructions_frame, text=instructions, 
                              font=("Arial", 10), justify=LEFT, 
                              bg="lightyellow", padx=15, pady=15, 
                              wraplength=500)
    instructions_label.pack(fill=X)

    def generate_user_qr():
        nonlocal secret_key, qr_label, secret_entry
        
        user_email = user_entry.get().strip()
        if not user_email:
            messagebox.showerror("Missing Information", 
                               "Please enter your name/email first!\n\n"
                               "This helps identify your AppLocker account.")
            return
        
        # Update progress to step 2
        update_progress(1)
        
        # Validate email format (basic validation)
        if "@" not in user_email and user_email != "quickuser@example.com":
            result = messagebox.askyesno("Email Format", 
                                       f"'{user_email}' doesn't look like an email address.\n\n"
                                       f"Continue anyway?")
            if not result:
                return
            
        # Generate secret key for this specific user
        try:
            secret_key = generate_secret_key()
            log_event(f"Generated secret key for user: {user_email}")
            
            # Update status
            qr_label.config(image="", text="Generating QR code...", 
                           fg="blue", bg="white", compound='none')
            setup_win.update()
            
        except Exception as e:
            log_error(f"Failed to generate secret key: {e}")
            messagebox.showerror("Generation Failed", 
                               f"Failed to generate secret key: {str(e)}")
            return
        
        try:
            # Generate QR code with user's email
            qr_code_path = generate_qr_code(secret_key, user_email)
            
            # Load and display QR code
            if os.path.exists(qr_code_path):
                img = Image.open(qr_code_path)
                # Resize to fit the frame properly - use larger size
                img = img.resize((260, 260), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # Update label to show image with proper sizing
                qr_label.config(image=photo, text="", compound='none', 
                               width=260, height=260)
                qr_label.image = photo  # Keep a reference to prevent garbage collection
                log_event("QR code displayed successfully")
                
                # Update progress to step 3 (scan code)
                update_progress(2)
                
                # Show success message
                messagebox.showinfo("QR Code Ready!", 
                                   f"QR code generated for {user_email}!\n\n"
                                   f"📱 Open Google Authenticator\n"
                                   f"📸 Scan the QR code below\n"
                                   f"✅ Then click 'Complete Setup'")
            else:
                qr_label.config(image="", text="❌ QR Code file not found!", 
                               fg="red", bg="white", compound='none')
                messagebox.showerror("File Error", "QR code file was not created properly.")
            
            # Update secret key display
            secret_entry.config(state=NORMAL)
            secret_entry.delete(0, END)
            secret_entry.insert(0, secret_key)
            secret_entry.config(state=DISABLED)
            
        except Exception as e:
            qr_label.config(image="", text=f"❌ QR Generation Error:\n{str(e)}", 
                           fg="red", bg="white")
            log_error(f"QR code generation error: {e}")
            # Show detailed error to user
            messagebox.showerror("QR Code Error", 
                               f"Failed to generate QR code:\n{str(e)}\n\n"
                               f"Please check:\n"
                               f"• Internet connection\n"
                               f"• App permissions\n"
                               f"• Disk space\n\n"
                               f"Try again or use Quick Setup.")

    # Generate QR button
    Button(main_frame, text="Generate My QR Code", command=generate_user_qr, 
           bg="lightblue", font=("Arial", 12, "bold"), pady=5).pack(pady=10)

    # Quick setup button for impatient users
    def quick_setup():
        """Generate QR code automatically with default email"""
        user_email = user_entry.get().strip()
        if not user_email or user_email == "user@example.com":
            user_entry.delete(0, END)
            user_entry.insert(0, "quickuser@example.com")
        generate_user_qr()
    
    Button(main_frame, text="⚡ Quick Setup (Auto-generate)", command=quick_setup,
           bg="yellow", font=("Arial", 10, "bold"), pady=3).pack(pady=2)

    # Reset authenticator button (if user already exists)
    def show_reset_option():
        existing_email = get_user_email_from_storage()
        if existing_email:
            # Simple "Show QR Code Again" button
            show_qr_btn = Button(main_frame, text="Show My QR Code Again", 
                               command=lambda: show_existing_qr_code(existing_email),
                               bg="lightgreen", font=("Arial", 10), pady=3)
            show_qr_btn.pack(pady=2)
            
            # Reset button for complete reset
            reset_btn = Button(main_frame, text="Reset Everything (Email Verification)", 
                             command=lambda: show_reset_authenticator_window(existing_email),
                             bg="orange", font=("Arial", 10), pady=3)
            reset_btn.pack(pady=2)
            
            # Nuclear option - reset everything immediately
            nuclear_btn = Button(main_frame, text="🔥 Reset App Completely (No Email)", 
                                command=lambda: reset_app_completely(),
                                bg="red", fg="white", font=("Arial", 9, "bold"), pady=3)
            nuclear_btn.pack(pady=2)
    
    show_reset_option()

    # QR Code display frame with fixed size
    qr_frame = Frame(main_frame, relief=SUNKEN, bd=2, bg="white", width=280, height=280)
    qr_frame.pack(pady=10)
    qr_frame.pack_propagate(False)  # Maintain fixed size
    
    qr_label = Label(qr_frame, text="Click 'Generate My QR Code' above", 
                    font=("Arial", 10), fg="gray", bg="white", 
                    wraplength=250, justify=CENTER)
    qr_label.place(relx=0.5, rely=0.5, anchor=CENTER)  # Center the label
    
    # Secret key display (for manual entry)
    secret_frame = Frame(main_frame)
    secret_frame.pack(fill=X, pady=10)
    
    Label(secret_frame, text="Manual Entry Key (if QR scan fails):", font=("Arial", 10, "bold")).pack(anchor=W)
    secret_entry = Entry(secret_frame, font=("Courier", 10), width=50, state=DISABLED)
    secret_entry.pack(fill=X, pady=5)

    def complete_setup():
        if not secret_key:
            messagebox.showerror("Setup Incomplete", 
                               "Please generate your QR code first!\n\n"
                               "Steps:\n"
                               "1. Click 'Generate My QR Code'\n"
                               "2. Scan the QR code with Google Authenticator\n"
                               "3. Then click 'Complete Setup'")
            return
            
        user_email = user_entry.get().strip()
        if not user_email:
            messagebox.showerror("Missing Information", 
                               "Please enter your name/email for identification!")
            return
        
        if user_email == "user@example.com":
            result = messagebox.askyesno("Confirm Email", 
                                       f"You're using the default email: {user_email}\n\n"
                                       f"Would you like to change it to your actual email?")
            if result:
                return
        
        # Final confirmation
        confirm = messagebox.askyesno("Complete Setup", 
                                    f"Complete AppLocker setup for:\n{user_email}\n\n"
                                    f"Make sure you've scanned the QR code with Google Authenticator!\n\n"
                                    f"Continue?")
        
        if not confirm:
            return
            
        try:
            # Save secret key with user info
            save_secret_to_db(secret_key, user_email)
            log_event(f"Setup completed for user: {user_email}")
            
            # Update progress to final step
            update_progress(3)
            
            # Success message with next steps
            messagebox.showinfo("🎉 Setup Complete!", 
                               f"AppLocker setup successful for {user_email}!\n\n"
                               f"✅ Google Authenticator configured\n"
                               f"✅ User account created\n"
                               f"✅ Ready to lock applications\n\n"
                               f"Next: Choose apps to lock with authenticator protection.")
            
            setup_win.destroy()
            show_installed_apps()
            
        except Exception as e:
            log_error(f"Setup failed: {e}")
            messagebox.showerror("Setup Failed", 
                               f"Failed to complete setup: {str(e)}\n\n"
                               f"Please try again or contact support.")

    # Setup button - make it more prominent
    setup_button_frame = Frame(main_frame, bg="lightgreen", relief="raised", bd=3)
    setup_button_frame.pack(pady=30, padx=20, fill=X)
    
    Button(setup_button_frame, text="✅ Complete Setup", command=complete_setup, 
           bg="lightgreen", font=("Arial", 14, "bold"), pady=15, width=20).pack(pady=10)
    
    Label(setup_button_frame, text="Click here after scanning the QR code", 
          font=("Arial", 10), bg="lightgreen", fg="darkgreen").pack(pady=(0, 10))

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
    apps = get_installed_apps()  # Get the list of installed apps
    if not apps:
        messagebox.showerror("Error", "No apps found.")
        return

    # Display apps in a new window
    apps_win = Tk()
    apps_win.title("Select Apps to Lock")
    apps_win.geometry("800x600")
    apps_win.resizable(True, True)

    # Main frame
    main_frame = Frame(apps_win, padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Title
    title_label = Label(main_frame, text=f"Found {len(apps)} Installed Applications", 
                       font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))
    
    # Search frame
    search_frame = Frame(main_frame)
    search_frame.pack(fill=X, pady=(0, 10))
    
    Label(search_frame, text="Search:", font=("Arial", 10)).pack(side=LEFT)
    search_entry = Entry(search_frame, font=("Arial", 10))
    search_entry.pack(side=LEFT, padx=(5, 10), fill=X, expand=True)
    
    # Create a frame to hold the listbox and the scrollbar
    list_frame = Frame(main_frame)
    list_frame.pack(fill=BOTH, expand=True)

    # Add scrollbars to the listbox
    v_scrollbar = Scrollbar(list_frame, orient=VERTICAL)
    h_scrollbar = Scrollbar(list_frame, orient=HORIZONTAL)
    
    listbox = Listbox(list_frame, 
                     height=20, 
                     font=("Arial", 10),
                     yscrollcommand=v_scrollbar.set,
                     xscrollcommand=h_scrollbar.set,
                     selectmode=SINGLE)
    
    # Populate listbox with apps
    for app in sorted(apps):
        listbox.insert(END, app)
    
    # Configure scrollbars
    v_scrollbar.config(command=listbox.yview)
    h_scrollbar.config(command=listbox.xview)
    
    # Pack scrollbars and listbox
    listbox.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")
    
    # Configure grid weights
    list_frame.grid_rowconfigure(0, weight=1)
    list_frame.grid_columnconfigure(0, weight=1)
    
    def search_apps():
        search_query = search_entry.get().lower()
        listbox.delete(0, END)
        for app in sorted(apps):
            if search_query in app.lower():
                listbox.insert(END, app)

    search_entry.bind('<KeyRelease>', lambda e: search_apps())
    
    # Buttons frame
    btn_frame = Frame(main_frame)
    btn_frame.pack(fill=X, pady=(10, 0))

    Button(btn_frame, text="Lock Selected App", 
           command=lambda: lock_selected_app(listbox.get(ACTIVE), apps_win),
           bg="lightcoral", font=("Arial", 11, "bold")).pack(side=LEFT, padx=(0, 10))
           
    Button(btn_frame, text="Refresh List", 
           command=lambda: refresh_app_list(listbox),
           bg="lightblue", font=("Arial", 11)).pack(side=LEFT, padx=(0, 10))
           
    Button(btn_frame, text="Back to Main", 
           command=lambda: [apps_win.destroy(), show_unlock_interface()],
           bg="lightgray", font=("Arial", 11)).pack(side=RIGHT)

def refresh_app_list(listbox):
    """Refresh the app list"""
    apps = get_installed_apps()
    listbox.delete(0, END)
    for app in sorted(apps):
        listbox.insert(END, app)

def lock_selected_app(app_name, parent_window=None):
    if app_name:
        # Confirm locking
        result = messagebox.askyesno("Confirm Lock", 
                                   f"Lock '{app_name}' with Google Authenticator?\n\n"
                                   f"You will need your authenticator code to unlock it.")
        
        if result:
            # Save app as locked (no PIN needed)
            try:
                with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
                    locked_apps = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                locked_apps = {}

            locked_apps[app_name] = True  # Just mark as locked

            with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                json.dump(locked_apps, file, indent=2)

            log_event(f"App '{app_name}' is now locked")
            messagebox.showinfo("App Locked", f"'{app_name}' is now protected with Google Authenticator!")
            
            # Close parent window if provided
            if parent_window:
                parent_window.destroy()
                show_unlock_interface()
    else:
        messagebox.showerror("Error", "Please select an app to lock.")

def show_unlock_interface():
    """Show the main unlock interface for managing locked apps"""
    unlock_win = Tk()
    unlock_win.title(WINDOW_TITLE)
    unlock_win.geometry("600x500")
    
    # Load locked apps
    try:
        with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
            locked_apps = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        locked_apps = {}
    
    if not locked_apps:
        Label(unlock_win, text="No apps are currently locked.", font=("Arial", 12)).pack(pady=20)
        Button(unlock_win, text="Lock New Apps", command=lambda: [unlock_win.destroy(), show_installed_apps()]).pack(pady=10)
        Button(unlock_win, text="Exit", command=unlock_win.destroy).pack(pady=5)
    else:
        Label(unlock_win, text="Locked Apps:", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create listbox for locked apps
        frame = Frame(unlock_win)
        frame.pack(pady=10, padx=20, fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(frame, orient=VERTICAL)
        listbox = Listbox(frame, height=10, yscrollcommand=scrollbar.set, font=("Arial", 10))
        
        for app in locked_apps.keys():
            listbox.insert(END, app)
        
        listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Buttons frame
        btn_frame = Frame(unlock_win)
        btn_frame.pack(pady=10)
        
        def unlock_selected():
            selection = listbox.curselection()
            if selection:
                app_name = listbox.get(selection[0])
                unlock_app(app_name)
        
        def remove_lock():
            selection = listbox.curselection()
            if selection:
                app_name = listbox.get(selection[0])
                result = messagebox.askyesno("Confirm", f"Remove lock from '{app_name}'?")
                if result:
                    del locked_apps[app_name]
                    with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                        json.dump(locked_apps, file, indent=2)
                    listbox.delete(selection[0])
                    log_event(f"Lock removed from app: {app_name}")
        
        Button(btn_frame, text="Unlock Selected", command=unlock_selected, bg="lightgreen").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Remove Lock", command=remove_lock, bg="lightcoral").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Lock New Apps", command=lambda: [unlock_win.destroy(), show_installed_apps()]).pack(side=LEFT, padx=5)
        
        # Add QR code and reset options
        Button(btn_frame, text="Show My QR Code", command=lambda: show_my_qr_from_main(), bg="lightblue").pack(side=LEFT, padx=5)
        Button(btn_frame, text="🔥 Reset All", command=lambda: reset_app_completely(), bg="red", fg="white").pack(side=LEFT, padx=5)
        
        Button(btn_frame, text="Exit", command=unlock_win.destroy).pack(side=LEFT, padx=5)
    
    unlock_win.mainloop()

def show_my_qr_from_main():
    """Show QR code from main interface"""
    user_email = get_user_email_from_storage()
    if user_email:
        show_existing_qr_code(user_email)
    else:
        messagebox.showerror("Error", "No user setup found. Please restart AppLocker to set up.")

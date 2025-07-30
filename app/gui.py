import json
import pyotp
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
    setup_win.geometry("600x850")  # Much taller to show all elements
    setup_win.resizable(True, True)  # Allow resizing
    
    # Main frame
    main_frame = Frame(setup_win, padx=20, pady=20)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Title
    title_label = Label(main_frame, text="AppLocker Setup", font=("Arial", 16, "bold"))
    title_label.pack(pady=(0, 10))
    
    # User identification frame
    user_frame = Frame(main_frame)
    user_frame.pack(fill=X, pady=(0, 20))
    
    Label(user_frame, text="Enter your name/email (for identification):", font=("Arial", 10, "bold")).pack(anchor=W)
    user_entry = Entry(user_frame, font=("Arial", 12), width=40)
    user_entry.pack(fill=X, pady=5)
    user_entry.insert(0, "user@example.com")
    
    # Instructions
    instructions = """
    Steps:
    1. Enter your name/email above
    2. Install Google Authenticator on your phone
    3. Scan the QR code below (or enter the key manually)
    4. Click 'Complete Setup' to finish
    
    Each user gets their own unique setup!
    """
    
    instructions_label = Label(main_frame, text=instructions, font=("Arial", 10), justify=LEFT, bg="lightyellow", padx=10, pady=10)
    instructions_label.pack(fill=X, pady=(0, 20))

    # Variables for QR code
    secret_key = None
    qr_label = None
    secret_entry = None

    def generate_user_qr():
        nonlocal secret_key, qr_label, secret_entry
        
        user_email = user_entry.get().strip()
        if not user_email:
            messagebox.showerror("Error", "Please enter your name/email first!")
            return
            
        # Generate secret key for this specific user
        secret_key = generate_secret_key()
        log_event(f"Generated secret key for user: {user_email}")
        
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
            else:
                qr_label.config(image="", text="QR Code file not found!", 
                               fg="red", bg="white", compound='none')
            
            # Update secret key display
            secret_entry.config(state=NORMAL)
            secret_entry.delete(0, END)
            secret_entry.insert(0, secret_key)
            secret_entry.config(state=DISABLED)
            
        except Exception as e:
            qr_label.config(image="", text=f"QR Generation Error:\n{str(e)}", fg="red", bg="white")
            log_error(f"QR code generation error: {e}")
            # Show detailed error to user
            messagebox.showerror("QR Code Error", f"Failed to generate QR code:\n{str(e)}")
            
    # Import os for file checking
    import os

    # Generate QR button
    Button(main_frame, text="Generate My QR Code", command=generate_user_qr, 
           bg="lightblue", font=("Arial", 12, "bold"), pady=5).pack(pady=10)

    # Reset authenticator button (if user already exists)
    def show_reset_option():
        existing_email = get_user_email_from_storage()
        if existing_email:
            reset_btn = Button(main_frame, text="Reset Authenticator (Lost QR Code)", 
                             command=lambda: show_reset_authenticator_window(existing_email),
                             bg="orange", font=("Arial", 10), pady=3)
            reset_btn.pack(pady=5)
    
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
            messagebox.showerror("Error", "Please generate your QR code first!")
            return
            
        user_email = user_entry.get().strip()
        if not user_email:
            messagebox.showerror("Error", "Please enter your name/email!")
            return
            
        # Save secret key with user info
        save_secret_to_db(secret_key, user_email)
        log_event(f"Setup completed for user: {user_email}")
        messagebox.showinfo("Setup Complete", 
                           f"Google Authenticator setup complete for {user_email}!\n"
                           f"You can now lock applications.")
        setup_win.destroy()
        show_installed_apps()

    # Setup button
    Button(main_frame, text="Complete Setup", command=complete_setup, 
           bg="lightgreen", font=("Arial", 12, "bold"), pady=10).pack(pady=20)

    setup_win.mainloop()

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
        Button(btn_frame, text="Exit", command=unlock_win.destroy).pack(side=LEFT, padx=5)
    
    unlock_win.mainloop()

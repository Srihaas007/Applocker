import json
import pyotp
import qrcode
from tkinter import *
from tkinter import simpledialog, messagebox
from tkinter import ttk
from PIL import ImageTk, Image
from app.logging import log_event
from app.user_data import hash_pin
from app.auth import save_pin_to_db, unlock_app
from app.app_lock import get_installed_apps
from app.config import QR_CODE_FILE, LOCKED_APPS_FILE, WINDOW_TITLE, QR_CODE_SIZE

# Function to generate a secret key for Google Authenticator
def generate_secret_key():
    secret = pyotp.random_base32()  # Generate a random secret key
    log_event(f"Generated new secret key: {secret}")
    return secret

# Function to generate a QR Code for Google Authenticator setup
def generate_qr_code(secret, email):
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(email, issuer_name="AppLocker")
    img = qrcode.make(uri)
    img.save(QR_CODE_FILE)  # Save the QR code image
    log_event(f"QR code saved to {QR_CODE_FILE}.")
    return QR_CODE_FILE

# Function to display QR Code
def display_qr_code(qr_code_path):
    img = Image.open(qr_code_path)
    img = img.resize(QR_CODE_SIZE)
    img = ImageTk.PhotoImage(img)
    qr_label.config(image=img)
    qr_label.image = img
    log_event("QR code displayed to user.")

# Function to handle user setup for PIN and QR code generation
def user_setup():
    setup_win = Tk()
    setup_win.title(f"{WINDOW_TITLE} - Setup")
    setup_win.geometry("400x500")

    # Entry for PIN
    Label(setup_win, text="Enter your PIN").grid(row=0, column=0)
    pin_entry = Entry(setup_win, show="*")
    pin_entry.grid(row=0, column=1)

    # Generate secret key for Google Authenticator and create QR code
    secret_key = generate_secret_key()
    qr_code_path = generate_qr_code(secret_key, "user@example.com")

    # Display QR Code
    global qr_label
    qr_label = Label(setup_win)
    qr_label.grid(row=1, column=0, columnspan=2)
    display_qr_code(qr_code_path)

    def save_data():
        pin = pin_entry.get()
        if pin:
            # Save the hashed PIN to a file or database (securely)
            hashed_pin = hash_pin(pin)
            save_pin_to_db(hashed_pin, secret_key)  # Save the hashed PIN and secret key
            log_event(f"User PIN and Secret Key saved successfully.")
            messagebox.showinfo("Setup Complete", "Your PIN and Secret Key have been saved!")
            setup_win.destroy()

            # Show installed apps after setup
            show_installed_apps()

    Button(setup_win, text="Save", command=save_data).grid(row=2, column=0, columnspan=2)

    setup_win.mainloop()

def show_installed_apps():
    apps = get_installed_apps()  # Get the list of installed apps
    if not apps:
        messagebox.showerror("Error", "No apps found.")
        return

    # Display apps in a new window
    apps_win = Toplevel()
    apps_win.title("Select Apps to Lock")

    # Create a frame to hold the listbox and the scrollbar
    frame = Frame(apps_win)
    frame.grid(row=0, column=0, padx=10, pady=10)

    # Add a scrollbar to the listbox
    scrollbar = Scrollbar(frame, orient=VERTICAL)
    listbox = Listbox(frame, height=15, width=50, yscrollcommand=scrollbar.set)
    for app in apps:
        listbox.insert(END, app)
    
    listbox.grid(row=0, column=0)
    scrollbar.config(command=listbox.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')

    # Create a search bar to filter the apps
    search_label = Label(frame, text="Search App:")
    search_label.grid(row=1, column=0)
    
    search_entry = Entry(frame)
    search_entry.grid(row=1, column=1)
    
    def search_apps():
        search_query = search_entry.get().lower()
        listbox.delete(0, END)
        for app in apps:
            if search_query in app.lower():
                listbox.insert(END, app)

    search_button = Button(frame, text="Search", command=search_apps)
    search_button.grid(row=1, column=2)

    Button(apps_win, text="Lock Selected App", command=lambda: lock_selected_app(listbox.get(ACTIVE))).grid(row=1, column=0, columnspan=2)

def lock_selected_app(app_name):
    if app_name:
        pin = simpledialog.askstring("PIN", f"Enter PIN to lock the app '{app_name}':", show="*")
        if pin:
            # Save app and PIN association in a JSON file
            try:
                with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
                    locked_apps = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                locked_apps = {}

            locked_apps[app_name] = hash_pin(pin).decode()

            with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                json.dump(locked_apps, file, indent=2)

            log_event(f"App '{app_name}' is locked with PIN")
            messagebox.showinfo("App Locked", f"The app '{app_name}' is now locked with your PIN.")
        else:
            messagebox.showerror("Error", "PIN is required to lock the app.")
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

"""
Process management module for AppLocker
Handles blocking and unblocking of applications
"""

import subprocess
import psutil
import time
import threading
from app.logging import log_event, log_error
from app.config import LOCKED_APPS_FILE
import json
import os

class AppBlocker:
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start monitoring for locked applications"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
            self.monitor_thread.start()
            log_event("App monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        log_event("App monitoring stopped")
    
    def _monitor_processes(self):
        """Monitor running processes and block locked apps"""
        while self.monitoring:
            try:
                locked_apps = self._get_locked_apps()
                
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name']
                        
                        # Check if any locked app name is in the process name
                        for locked_app in locked_apps:
                            if self._app_matches_process(locked_app, proc_name):
                                log_event(f"Detected locked app running: {proc_name}")
                                self._block_process(proc, locked_app)
                                
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                log_error(f"Error in process monitoring: {e}")
                time.sleep(5)
    
    def _get_locked_apps(self):
        """Get list of locked applications"""
        try:
            with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
                locked_apps = json.load(file)
                return [app for app, locked in locked_apps.items() if locked]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _app_matches_process(self, app_name, process_name):
        """Check if app name matches process name"""
        # Simple matching - can be improved
        app_words = app_name.lower().split()
        process_lower = process_name.lower()
        
        # Check if any word from app name is in process name
        for word in app_words:
            if len(word) > 3 and word in process_lower:
                return True
                
        # Check exact matches for common executables
        common_mappings = {
            'chrome': 'chrome.exe',
            'firefox': 'firefox.exe',
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe',
            'paint': 'mspaint.exe',
            'steam': 'steam.exe',
            'discord': 'discord.exe',
            'spotify': 'spotify.exe',
            'skype': 'skype.exe',
            'zoom': 'zoom.exe'
        }
        
        for app_key, exe_name in common_mappings.items():
            if app_key in app_name.lower() and exe_name == process_name.lower():
                return True
                
        return False
    
    def _block_process(self, process, app_name):
        """Block a process by terminating it"""
        try:
            # Show blocking message in a separate thread to avoid blocking monitor
            threading.Thread(target=self._show_block_message, args=(app_name,), daemon=True).start()
            
            # Terminate the process
            process.terminate()
            log_event(f"Blocked process: {process.info['name']} for app: {app_name}")
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log_error(f"Failed to block process: {e}")
    
    def _show_block_message(self, app_name):
        """Show blocking message to user"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Create a temporary root window
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            
            messagebox.showwarning("App Blocked", 
                                 f"'{app_name}' is locked!\n\n"
                                 f"Use AppLocker to unlock it with your authenticator code.")
            
            root.destroy()
            
        except Exception as e:
            log_error(f"Failed to show block message: {e}")

# Global app blocker instance
app_blocker = AppBlocker()

def start_app_blocking():
    """Start the app blocking service"""
    app_blocker.start_monitoring()

def stop_app_blocking():
    """Stop the app blocking service"""
    app_blocker.stop_monitoring()

def unlock_app_temporarily(app_name, duration_minutes=60):
    """Temporarily unlock an app for specified duration"""
    try:
        with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
            locked_apps = json.load(file)
            
        if app_name in locked_apps:
            locked_apps[app_name] = False  # Temporarily unlock
            
            with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                json.dump(locked_apps, file, indent=2)
            
            log_event(f"App '{app_name}' temporarily unlocked for {duration_minutes} minutes")
            
            # Re-lock after duration
            def re_lock():
                time.sleep(duration_minutes * 60)
                try:
                    with open(LOCKED_APPS_FILE, "r", encoding="utf-8") as file:
                        locked_apps = json.load(file)
                    locked_apps[app_name] = True  # Re-lock
                    with open(LOCKED_APPS_FILE, "w", encoding="utf-8") as file:
                        json.dump(locked_apps, file, indent=2)
                    log_event(f"App '{app_name}' automatically re-locked")
                except Exception as e:
                    log_error(f"Failed to re-lock app: {e}")
            
            threading.Thread(target=re_lock, daemon=True).start()
            
    except Exception as e:
        log_error(f"Failed to unlock app temporarily: {e}")

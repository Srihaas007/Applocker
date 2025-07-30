import winreg
import os
from app.logging import log_error, log_debug
from app.config import UNINSTALL_KEY, UWP_APPS_KEY

def get_installed_apps():
    installed_apps = []
    
    # Check traditional app registry
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, UNINSTALL_KEY)
        
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sub_key = winreg.EnumKey(key, i)
                sub_key_path = os.path.join(UNINSTALL_KEY, sub_key)
                app_key = winreg.OpenKey(reg, sub_key_path)
                app_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                installed_apps.append(app_name)
                winreg.CloseKey(app_key)
            except (FileNotFoundError, OSError):
                continue
        
        winreg.CloseKey(key)
        winreg.CloseKey(reg)
        
    except Exception as e:
        log_error(f"Error reading installed apps: {e}")
    
    # Check Microsoft Store apps (UWP apps)
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, UWP_APPS_KEY)
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sub_key = winreg.EnumKey(key, i)
                sub_key_path = os.path.join(UWP_APPS_KEY, sub_key)
                app_key = winreg.OpenKey(reg, sub_key_path)
                app_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                installed_apps.append(app_name)
                winreg.CloseKey(app_key)
            except (FileNotFoundError, OSError):
                continue
                
        winreg.CloseKey(key)
        winreg.CloseKey(reg)
        
    except Exception as e:
        log_error(f"Error reading UWP apps: {e}")

    # Remove duplicates and sort
    installed_apps = sorted(list(set(installed_apps)))
    log_debug(f"Found {len(installed_apps)} installed applications")
    
    return installed_apps

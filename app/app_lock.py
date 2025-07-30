import winreg
import os

def get_installed_apps():
    installed_apps = []
    
    # Check traditional app registry
    uninstall_key = r"SOFTWARE/Microsoft/Windows/CurrentVersion/Uninstall"
    
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, uninstall_key)
        
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sub_key = winreg.EnumKey(key, i)
                sub_key_path = os.path.join(uninstall_key, sub_key)
                app_key = winreg.OpenKey(reg, sub_key_path)
                app_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                installed_apps.append(app_name)
            except FileNotFoundError:
                continue
    except Exception as e:
        print(f"Error reading installed apps: {e}")
    
    # Check Microsoft Store apps (UWP apps)
    uwp_apps_key = r"SOFTWARE/Microsoft/Windows/CurrentVersion/Uninstall/Microsoft"
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, uwp_apps_key)
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sub_key = winreg.EnumKey(key, i)
                sub_key_path = os.path.join(uwp_apps_key, sub_key)
                app_key = winreg.OpenKey(reg, sub_key_path)
                app_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                installed_apps.append(app_name)
            except FileNotFoundError:
                continue
    except Exception as e:
        print(f"Error reading UWP apps: {e}")

    return installed_apps

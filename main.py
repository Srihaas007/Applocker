from app.gui import user_setup
from app.auth import unlock_app
from app.config import USER_DATA_FILE
from app.process_manager import start_app_blocking, stop_app_blocking
import os
import atexit

# Initialize logging
from app.logging import setup_logging
setup_logging()

def check_setup():
    """Check if user setup is complete and valid"""
    if not os.path.exists(USER_DATA_FILE):
        return False
    
    # Check if setup file has valid data
    try:
        from app.auth import load_user_data
        secret_key, user_email = load_user_data()
        return secret_key is not None
    except Exception:
        return False

# Main entry point
if __name__ == '__main__':
    try:
        # Start app blocking service
        start_app_blocking()
        
        # Register cleanup function
        atexit.register(stop_app_blocking)
        
        if not check_setup():
            print("Setting up AppLocker for first time...")
            user_setup()  # Setup user 2FA
        else:
            print("AppLocker is running. App blocking is active.")
        
        # After setup, run the unlock app flow
        unlock_app()
        
    except KeyboardInterrupt:
        print("\nShutting down AppLocker...")
        stop_app_blocking()
    except Exception as e:
        print(f"Error: {e}")
        stop_app_blocking()

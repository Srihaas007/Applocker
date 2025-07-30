from app.gui import user_setup
from app.auth import unlock_app
import os

# Initialize logging
from app.logging import setup_logging
setup_logging()

def check_setup():
    """Check if user setup is complete"""
    return os.path.exists("user_data.txt")

# Main entry point
if __name__ == '__main__':
    if not check_setup():
        print("Setting up AppLocker for first time...")
        user_setup()  # Setup user PIN and 2FA
    else:
        print("AppLocker is already set up. Launching main interface...")
    
    # After setup, run the unlock app flow
    unlock_app()

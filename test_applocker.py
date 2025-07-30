"""
Test script for AppLocker functionality

This script tests various components of the AppLocker application
without requiring GUI interaction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.user_data import hash_pin, verify_pin
from app.auth import save_pin_to_db, load_user_data, verify_totp
from app.app_lock import get_installed_apps
from app.logging import setup_logging, log_event
import pyotp

def test_pin_hashing():
    """Test PIN hashing and verification"""
    print("Testing PIN hashing...")
    
    test_pin = "1234"
    hashed = hash_pin(test_pin)
    
    # Verify correct PIN
    if verify_pin(hashed, test_pin):
        print("✅ PIN hashing and verification: PASS")
    else:
        print("❌ PIN hashing and verification: FAIL")
        return False
        
    # Verify incorrect PIN
    if not verify_pin(hashed, "wrong"):
        print("✅ PIN rejection: PASS")
    else:
        print("❌ PIN rejection: FAIL")
        return False
        
    return True

def test_totp():
    """Test TOTP functionality"""
    print("Testing TOTP...")
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    
    # Test with current code
    if verify_totp(secret, current_code):
        print("✅ TOTP verification: PASS")
    else:
        print("❌ TOTP verification: FAIL")
        return False
        
    # Test with wrong code
    if not verify_totp(secret, "000000"):
        print("✅ TOTP rejection: PASS")
    else:
        print("❌ TOTP rejection: FAIL")
        return False
        
    return True

def test_app_discovery():
    """Test app discovery functionality"""
    print("Testing app discovery...")
    
    apps = get_installed_apps()
    
    if isinstance(apps, list) and len(apps) > 0:
        print(f"✅ App discovery: PASS (Found {len(apps)} apps)")
        return True
    else:
        print("❌ App discovery: FAIL")
        return False

def test_data_persistence():
    """Test data saving and loading"""
    print("Testing data persistence...")
    
    test_pin = "test123"
    hashed_pin = hash_pin(test_pin)
    test_secret = pyotp.random_base32()
    
    # Save data
    try:
        save_pin_to_db(hashed_pin, test_secret)
        print("✅ Data saving: PASS")
    except Exception as e:
        print(f"❌ Data saving: FAIL - {e}")
        return False
    
    # Load data
    try:
        loaded_pin, loaded_secret = load_user_data()
        if loaded_pin and loaded_secret == test_secret:
            print("✅ Data loading: PASS")
        else:
            print("❌ Data loading: FAIL - Data mismatch")
            return False
    except Exception as e:
        print(f"❌ Data loading: FAIL - {e}")
        return False
        
    return True

def main():
    """Run all tests"""
    print("🔒 AppLocker Test Suite")
    print("=" * 40)
    
    # Setup logging
    setup_logging()
    
    tests = [
        test_pin_hashing,
        test_totp,
        test_app_discovery,
        test_data_persistence
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAIL - {e}")
        print()
    
    print("=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        log_event("All tests passed successfully")
        return True
    else:
        print("⚠️  Some tests failed!")
        log_event(f"Tests failed: {total - passed}/{total}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

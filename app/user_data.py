import bcrypt

# Function to hash the PIN securely
def hash_pin(pin):
    salt = bcrypt.gensalt()  # Generate salt for bcrypt
    hashed_pin = bcrypt.hashpw(pin.encode('utf-8'), salt)  # Hash the PIN with salt
    return hashed_pin

# Function to verify the PIN
def verify_pin(stored_hashed_pin, entered_pin):
    return bcrypt.checkpw(entered_pin.encode('utf-8'), stored_hashed_pin)

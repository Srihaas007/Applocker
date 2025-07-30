# AppLocker API Documentation

## Module Overview

AppLocker consists of several modules that work together to provide secure application locking functionality.

## Core Modules

### app.config

Configuration management for the application.

**Constants:**
- `APP_NAME`: Application name
- `APP_VERSION`: Current version
- `USER_DATA_FILE`: Path to user data storage
- `LOCKED_APPS_FILE`: Path to locked apps database
- `MIN_PIN_LENGTH`: Minimum PIN length (4)
- `MAX_PIN_LENGTH`: Maximum PIN length (12)

### app.auth

Authentication and security functions.

#### Functions

```python
def save_pin_to_db(hashed_pin: bytes, secret_key: str) -> None
```
Saves hashed PIN and 2FA secret to storage.

**Parameters:**
- `hashed_pin`: bcrypt-hashed PIN bytes
- `secret_key`: Base32 TOTP secret key

```python
def load_user_data() -> Tuple[str, str]
```
Loads user credentials from storage.

**Returns:**
- Tuple of (hashed_pin, secret_key) or (None, None) if not found

```python
def verify_totp(secret: str, entered_code: str) -> bool
```
Verifies TOTP code against secret.

**Parameters:**
- `secret`: Base32 TOTP secret
- `entered_code`: 6-digit code from authenticator

**Returns:**
- True if code is valid

```python
def verify_pin(stored_hashed_pin: bytes, entered_pin: str) -> bool
```
Verifies PIN against stored hash.

**Parameters:**
- `stored_hashed_pin`: Stored bcrypt hash
- `entered_pin`: User-entered PIN

**Returns:**
- True if PIN matches

```python
def unlock_app(app_name: str = None) -> None
```
Main unlock function. If no app_name provided, shows main interface.

### app.user_data

User data handling functions.

```python
def hash_pin(pin: str) -> bytes
```
Hashes PIN using bcrypt with random salt.

**Parameters:**
- `pin`: Plain text PIN

**Returns:**
- bcrypt hash bytes

### app.app_lock

Windows application discovery.

```python
def get_installed_apps() -> List[str]
```
Discovers installed Windows applications.

**Returns:**
- List of application names

### app.gui

Graphical user interface functions.

```python
def user_setup() -> None
```
Initial setup interface for PIN and 2FA configuration.

```python
def show_installed_apps() -> None
```
Interface for selecting apps to lock.

```python
def show_unlock_interface() -> None
```
Main application management interface.

```python
def generate_secret_key() -> str
```
Generates random Base32 secret for TOTP.

```python
def generate_qr_code(secret: str, email: str) -> str
```
Creates QR code for Google Authenticator setup.

### app.logging

Logging system with rotation support.

```python
def setup_logging() -> None
```
Configures rotating file and console logging.

```python
def log_event(message: str) -> None
```
Logs informational events.

```python
def log_error(message: str) -> None
```
Logs error messages.

```python
def log_warning(message: str) -> None
```
Logs warning messages.

```python
def log_debug(message: str) -> None
```
Logs debug information.

## Data Formats

### User Data File Format
```
{hashed_pin_base64}
{totp_secret_base32}
```

### Locked Apps JSON Format
```json
{
    "Application Name": "hashed_pin_base64",
    "Another App": "another_hashed_pin_base64"
}
```

## Security Considerations

### PIN Security
- PINs are hashed using bcrypt with random salt
- Minimum 4 digits, maximum 12 digits
- Never stored in plain text

### TOTP Security
- Uses standard RFC 6238 implementation
- 30-second time window
- Base32 encoded secrets
- Compatible with Google Authenticator

### Data Storage
- User data stored in local files
- No network communication for credentials
- Logs contain no sensitive information

## Error Handling

All functions include comprehensive error handling:
- File I/O errors are logged and handled gracefully
- Invalid inputs are validated
- User feedback provided through GUI messages

## Extension Points

### Adding New Authentication Methods
Extend the `app.auth` module to support additional authentication methods.

### Custom App Discovery
Modify `app.app_lock` to support additional application sources.

### UI Customization
The GUI module uses tkinter and can be extended with additional themes or layouts.

## Testing

Run the test suite:
```bash
python test_applocker.py
```

Tests cover:
- PIN hashing and verification
- TOTP generation and validation
- App discovery functionality
- Data persistence

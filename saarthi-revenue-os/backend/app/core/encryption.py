from cryptography.fernet import Fernet
from app.core.settings import settings

def _get_fernet():
    """Returns a Fernet instance using the global ENCRYPTION_KEY."""
    return Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_secret(value: str) -> str:
    """Encrypts a string value using Fernet."""
    if not value:
        return ""
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()

def decrypt_secret(value: str) -> str:
    """Decrypts a encrypted string back to plaintext."""
    if not value:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(value.encode()).decode()
    except Exception:
        return ""

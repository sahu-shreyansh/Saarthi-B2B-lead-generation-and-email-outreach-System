import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from passlib.context import CryptContext
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    user_id: str | Any, 
    org_id: str | Any, 
    role: str,
    token_version: int,
    expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Standard expiry 2 hours
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire, 
        "sub": str(user_id), 
        "active_org_id": str(org_id),
        "role": role,
        "token_version": token_version
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        decoded_token = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return decoded_token
    except jwt.PyJWTError:
        return None


# ── AES ENCRYPTION FOR TOKENS ─────────────────────

def encrypt_string(plaintext: str) -> str:
    if not plaintext:
        return ""
    aesgcm = AESGCM(settings.ENCRYPTION_KEY.encode('utf-8'))
    import os
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return nonce.hex() + ":" + ciphertext.hex()


def decrypt_string(encrypted_data: str) -> str:
    if not encrypted_data or ":" not in encrypted_data:
        return ""
    try:
        nonce_hex, ciphertext_hex = encrypted_data.split(":", 1)
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = bytes.fromhex(ciphertext_hex)
        aesgcm = AESGCM(settings.ENCRYPTION_KEY.encode('utf-8'))
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception:
        return ""

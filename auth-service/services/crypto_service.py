"""Field-level encryption using Fernet (AES-128-CBC + HMAC-SHA256)."""
import base64
import json
from typing import Any
from cryptography.fernet import Fernet
from config import get_settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key_raw = get_settings().ENCRYPTION_KEY
        # Fernet requires a 32-byte URL-safe base64 key
        key_bytes = key_raw.encode()[:32].ljust(32, b"0")
        key_b64 = base64.urlsafe_b64encode(key_bytes)
        _fernet = Fernet(key_b64)
    return _fernet


def encrypt(value: str) -> str:
    """Encrypt a plaintext string → URL-safe base64 ciphertext."""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a ciphertext string → plaintext."""
    return _get_fernet().decrypt(token.encode()).decode()


def encrypt_json(obj: Any) -> str:
    return encrypt(json.dumps(obj))


def decrypt_json(token: str) -> Any:
    return json.loads(decrypt(token))

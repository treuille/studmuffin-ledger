# secrets_manager.py
#
# Encrypted secrets management for Streamlit apps.
#
# We don't trust Streamlit Community Cloud with plaintext secrets.
# This module encrypts secrets with a password so they only exist
# decrypted in memory.
#
# Crypto choices:
# - Key derivation: scrypt (memory-hard, resists GPU attacks)
# - Encryption: Fernet (AES-128-CBC + HMAC-SHA256)
# - Encoding: base64 (standard, Fernet-native)

import base64
import json
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


# scrypt parameters (OWASP recommended for interactive login)
SCRYPT_N = 2**14  # CPU/memory cost
SCRYPT_R = 8  # block size
SCRYPT_P = 1  # parallelization
SCRYPT_LENGTH = 32  # output key length for Fernet


@dataclass
class EncryptedBlob:
    """Container for the encrypted secrets blob."""

    version: int
    salt: bytes
    ciphertext: bytes

    def to_string(self) -> str:
        """Encode blob as a single base64 string for storage."""
        payload = {
            "v": self.version,
            "s": base64.b64encode(self.salt).decode("ascii"),
            "c": base64.b64encode(self.ciphertext).decode("ascii"),
        }
        return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    @classmethod
    def from_string(cls, encoded: str) -> "EncryptedBlob":
        """Decode blob from a base64 string."""
        try:
            payload = json.loads(base64.b64decode(encoded))
            return cls(
                version=payload["v"],
                salt=base64.b64decode(payload["s"]),
                ciphertext=base64.b64decode(payload["c"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid encrypted blob format: {e}") from e


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from password using scrypt."""
    kdf = Scrypt(
        salt=salt,
        length=SCRYPT_LENGTH,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_secrets(secrets: dict, password: str) -> str:
    """
    Encrypt a secrets dictionary with a password.

    Args:
        secrets: Dictionary of secrets to encrypt
        password: Password to derive encryption key from

    Returns:
        Base64-encoded encrypted blob string
    """
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    fernet = Fernet(key)

    plaintext = json.dumps(secrets).encode("utf-8")
    ciphertext = fernet.encrypt(plaintext)

    blob = EncryptedBlob(version=1, salt=salt, ciphertext=ciphertext)
    return blob.to_string()


def decrypt_secrets(blob_string: str, password: str) -> dict:
    """
    Decrypt a secrets blob with a password.

    Args:
        blob_string: Base64-encoded encrypted blob
        password: Password to derive decryption key from

    Returns:
        Decrypted secrets dictionary

    Raises:
        ValueError: If blob format is invalid
        InvalidToken: If password is wrong or data is corrupted
    """
    blob = EncryptedBlob.from_string(blob_string)

    if blob.version != 1:
        raise ValueError(f"Unsupported blob version: {blob.version}")

    key = _derive_key(password, blob.salt)
    fernet = Fernet(key)

    plaintext = fernet.decrypt(blob.ciphertext)
    return json.loads(plaintext.decode("utf-8"))


class DecryptionError(Exception):
    """Raised when decryption fails (wrong password or corrupted data)."""

    pass


def try_decrypt_secrets(blob_string: str, password: str) -> tuple[dict | None, str | None]:
    """
    Try to decrypt secrets, returning (secrets, None) on success
    or (None, error_message) on failure.

    This is a convenience wrapper that catches exceptions and returns
    user-friendly error messages.
    """
    if not blob_string:
        return None, "No encrypted secrets found. Use Config page to set up secrets."

    if not password:
        return None, "Password is required."

    try:
        secrets = decrypt_secrets(blob_string, password)
        return secrets, None
    except ValueError as e:
        return None, f"Invalid secrets format: {e}"
    except InvalidToken:
        return None, "Wrong password or corrupted data."
    except Exception as e:
        return None, f"Decryption failed: {e}"

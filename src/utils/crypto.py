"""
Cryptography Utilities

Encryption and decryption utilities for sensitive data.
"""

import base64
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def generate_encryption_key() -> str:
    """
    Generate a random AES-256 encryption key.

    Returns:
        str: 64-character hex string (32 bytes)
    """
    key_bytes = secrets.token_bytes(32)
    return key_bytes.hex()


def encrypt_data(data: str, key_hex: str) -> str:
    """
    Encrypt data using AES-256-GCM.

    Args:
        data: Plain text data to encrypt
        key_hex: 64-character hex encryption key

    Returns:
        str: Base64-encoded encrypted data (nonce + ciphertext)

    Raises:
        ValueError: If key is invalid
    """
    if len(key_hex) != 64:
        raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

    # Convert hex to bytes
    key_bytes = bytes.fromhex(key_hex)

    # Create cipher
    aesgcm = AESGCM(key_bytes)

    # Generate random nonce (12 bytes for GCM)
    nonce = secrets.token_bytes(12)

    # Encrypt
    plaintext = data.encode('utf-8')
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # Combine nonce + ciphertext
    encrypted = nonce + ciphertext

    # Encode to base64
    return base64.b64encode(encrypted).decode('ascii')


def decrypt_data(encrypted_b64: str, key_hex: str) -> str:
    """
    Decrypt data using AES-256-GCM.

    Args:
        encrypted_b64: Base64-encoded encrypted data
        key_hex: 64-character hex encryption key

    Returns:
        str: Decrypted plain text

    Raises:
        ValueError: If decryption fails
    """
    if len(key_hex) != 64:
        raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

    try:
        # Convert hex to bytes
        key_bytes = bytes.fromhex(key_hex)

        # Create cipher
        aesgcm = AESGCM(key_bytes)

        # Decode from base64
        encrypted = base64.b64decode(encrypted_b64)

        # Extract nonce and ciphertext
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)

        return plaintext.decode('utf-8')

    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError(f"Decryption failed: {e}")


def hash_data(data: str) -> str:
    """
    Hash data using SHA-256.

    Args:
        data: Data to hash

    Returns:
        str: Hex-encoded hash
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


def test_encryption(key_hex: str) -> bool:
    """
    Test encryption/decryption with a key.

    Args:
        key_hex: Encryption key

    Returns:
        bool: True if test passes
    """
    try:
        test_data = "test_session_string_1234567890"
        encrypted = encrypt_data(test_data, key_hex)
        decrypted = decrypt_data(encrypted, key_hex)
        return test_data == decrypted
    except Exception as e:
        logger.error(f"Encryption test failed: {e}")
        return False

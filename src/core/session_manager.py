"""
Session String Encryption Manager

AES-256-GCM encryption for Telegram session strings.
"""

import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import secrets
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages encryption/decryption of Telegram session strings.

    Uses AES-256-GCM for authenticated encryption.
    """

    def __init__(self, encryption_key_hex: str):
        """
        Initialize session manager.

        Args:
            encryption_key_hex: 64-character hex string (32 bytes)
        """
        if len(encryption_key_hex) != 64:
            raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

        # Convert hex to bytes
        self.encryption_key = bytes.fromhex(encryption_key_hex)

        if len(self.encryption_key) != 32:
            raise ValueError("Encryption key must be 32 bytes (AES-256)")

        self.aesgcm = AESGCM(self.encryption_key)

    def encrypt_session(self, session_string: str) -> str:
        """
        Encrypt session string.

        Args:
            session_string: Telethon session string

        Returns:
            str: Base64-encoded encrypted data (nonce + ciphertext + tag)
        """
        if not session_string:
            raise ValueError("Session string cannot be empty")

        # Generate random nonce (12 bytes for GCM)
        nonce = secrets.token_bytes(12)

        # Encrypt
        plaintext = session_string.encode('utf-8')
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data=None)

        # Combine nonce + ciphertext
        encrypted_data = nonce + ciphertext

        # Encode to base64 for storage
        return base64.b64encode(encrypted_data).decode('ascii')

    def decrypt_session(self, encrypted_data_b64: str) -> str:
        """
        Decrypt session string.

        Args:
            encrypted_data_b64: Base64-encoded encrypted data

        Returns:
            str: Decrypted session string
        """
        if not encrypted_data_b64:
            raise ValueError("Encrypted data cannot be empty")

        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_data_b64)

            # Extract nonce and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # Decrypt
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, associated_data=None)

            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to decrypt session string: {e}")
            raise ValueError(f"Decryption failed: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a random AES-256 key.

        Returns:
            str: 64-character hex string (32 bytes)
        """
        key_bytes = secrets.token_bytes(32)
        return key_bytes.hex()

    def test_encryption(self) -> bool:
        """
        Test encryption/decryption functionality.

        Returns:
            bool: True if test passes
        """
        try:
            test_data = "test_session_string_1234567890"
            encrypted = self.encrypt_session(test_data)
            decrypted = self.decrypt_session(encrypted)
            return test_data == decrypted
        except Exception as e:
            logger.error(f"Encryption test failed: {e}")
            return False

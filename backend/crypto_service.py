"""Cryptographic service for secure API key storage."""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CryptoService:
    """Service for encrypting and decrypting sensitive data like API keys."""
    
    def __init__(self, master_key: Optional[str] = None):
        self._master_key = master_key or os.getenv("MASTER_KEY", "default_master_key_change_in_production")
        self._salt = b"TradingAgents_Salt_2024"
        self._fernet = self._derive_fernet_key()
    
    def _derive_fernet_key(self) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64 encoded ciphertext."""
        if not plaintext:
            return ""
        encrypted = self._fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64 encoded ciphertext."""
        if not ciphertext:
            return ""
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt: {e}")
            return ""
    
    def encrypt_api_key(self, api_key: str, api_secret: str) -> tuple[str, str]:
        """Encrypt API key and secret pair."""
        return self.encrypt(api_key), self.encrypt(api_secret)
    
    def decrypt_api_key(self, encrypted_key: str, encrypted_secret: str) -> tuple[str, str]:
        """Decrypt API key and secret pair."""
        return self.decrypt(encrypted_key), self.decrypt(encrypted_secret)


crypto_service = CryptoService()
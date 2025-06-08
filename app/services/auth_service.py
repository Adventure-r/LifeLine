"""
Authentication service
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from cryptography.fernet import Fernet
from loguru import logger

from app.config import settings
from app.database.models import InviteToken


class AuthService:
    """
    Service for handling authentication and authorization
    """
    
    @staticmethod
    def verify_admin_code(code: str) -> bool:
        """
        Verify admin authentication code
        
        Args:
            code: Admin code to verify
            
        Returns:
            bool: True if code is valid
        """
        try:
            return code in settings.ADMIN_CODES
        except Exception as e:
            logger.error(f"Error verifying admin code: {e}")
            return False
    
    @staticmethod
    def generate_invite_token() -> str:
        """
        Generate unique invite token
        
        Returns:
            str: Generated token
        """
        try:
            # Generate a secure random token
            token = secrets.token_urlsafe(32)
            return token
        except Exception as e:
            logger.error(f"Error generating invite token: {e}")
            return secrets.token_hex(16)  # Fallback
    
    @staticmethod
    def encrypt_token(token: str) -> str:
        """
        Encrypt token for storage
        
        Args:
            token: Token to encrypt
            
        Returns:
            str: Encrypted token
        """
        try:
            # Create Fernet cipher from secret key
            key = settings.SECRET_KEY.encode()
            # Ensure key is 32 bytes for Fernet
            if len(key) < 32:
                key = key.ljust(32, b'0')
            elif len(key) > 32:
                key = key[:32]
            
            # Encode to base64 for Fernet
            import base64
            key = base64.urlsafe_b64encode(key)
            
            cipher = Fernet(key)
            encrypted = cipher.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Error encrypting token: {e}")
            return token  # Return original if encryption fails
    
    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """
        Decrypt token from storage
        
        Args:
            encrypted_token: Encrypted token
            
        Returns:
            str: Decrypted token
        """
        try:
            # Create Fernet cipher from secret key
            key = settings.SECRET_KEY.encode()
            # Ensure key is 32 bytes for Fernet
            if len(key) < 32:
                key = key.ljust(32, b'0')
            elif len(key) > 32:
                key = key[:32]
            
            # Encode to base64 for Fernet
            import base64
            key = base64.urlsafe_b64encode(key)
            
            cipher = Fernet(key)
            decrypted = cipher.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting token: {e}")
            return encrypted_token  # Return original if decryption fails
    
    @staticmethod
    def is_token_valid(invite_token: InviteToken) -> bool:
        """
        Check if invite token is valid and not expired
        
        Args:
            invite_token: InviteToken object to validate
            
        Returns:
            bool: True if token is valid
        """
        try:
            if not invite_token.is_active:
                return False
            
            # Check expiration
            if invite_token.expires_at < datetime.now():
                return False
            
            # Check usage limit
            if invite_token.max_uses and invite_token.uses_count >= invite_token.max_uses:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
    
    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """
        Generate secure password
        
        Args:
            length: Password length
            
        Returns:
            str: Generated password
        """
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password for storage
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        import hashlib
        import salt
        
        try:
            # Generate salt
            salt_value = secrets.token_hex(16)
            # Hash password with salt
            hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt_value.encode(), 100000)
            # Combine salt and hash
            return f"{salt_value}:{hashed.hex()}"
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            return password  # Fallback (not secure)
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password
            hashed_password: Hashed password from storage
            
        Returns:
            bool: True if password matches
        """
        import hashlib
        
        try:
            # Split salt and hash
            salt_value, stored_hash = hashed_password.split(':')
            # Hash provided password with same salt
            hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt_value.encode(), 100000)
            # Compare hashes
            return hashed.hex() == stored_hash
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def validate_telegram_id(telegram_id: int) -> bool:
        """
        Validate Telegram user ID format
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            bool: True if valid
        """
        try:
            # Telegram user IDs are positive integers
            return isinstance(telegram_id, int) and telegram_id > 0
        except Exception as e:
            logger.error(f"Error validating Telegram ID: {e}")
            return False
    
    @staticmethod
    def sanitize_username(username: str) -> str:
        """
        Sanitize username for storage
        
        Args:
            username: Raw username
            
        Returns:
            str: Sanitized username
        """
        try:
            if not username:
                return ""
            
            # Remove @ if present
            username = username.lstrip('@')
            
            # Remove special characters except underscore
            import re
            username = re.sub(r'[^a-zA-Z0-9_]', '', username)
            
            # Limit length
            return username[:32]
        except Exception as e:
            logger.error(f"Error sanitizing username: {e}")
            return ""
    
    @staticmethod
    def generate_session_token() -> str:
        """
        Generate session token for temporary authentication
        
        Returns:
            str: Session token
        """
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def is_admin_telegram_id(telegram_id: int) -> bool:
        """
        Check if Telegram ID belongs to admin (from environment)
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            bool: True if user is admin
        """
        try:
            # This could be extended to check against a list of admin Telegram IDs
            # For now, we rely on admin codes for authentication
            return False
        except Exception as e:
            logger.error(f"Error checking admin Telegram ID: {e}")
            return False

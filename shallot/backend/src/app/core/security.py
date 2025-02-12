from datetime import datetime, timedelta
from typing import Any, Optional, Union

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext
from ..config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize Fernet cipher with encryption key
try:
    _cipher = Fernet(settings.ENCRYPTION_KEY.encode())
except Exception as e:
    print(f"Error initializing Fernet cipher: {str(e)}")
    print(f"Current encryption key: {settings.ENCRYPTION_KEY}")
    raise


def encrypt_value(value: str) -> str:
    """Encrypt a string value.

    Args:
        value: Plain text value to encrypt

    Returns:
        Encrypted value as a base64-encoded string
    """
    return _cipher.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted value.

    Args:
        encrypted_value: Base64-encoded encrypted string

    Returns:
        Decrypted plain text value
    """
    return _cipher.decrypt(encrypted_value.encode()).decode()


def generate_key() -> str:
    """Generate a new Fernet key.

    Returns:
        Base64-encoded 32-byte key
    """
    return Fernet.generate_key().decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to verify against

    Returns:
        True if password matches hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a hash from a password.

    Args:
        password: The password to hash

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    is_superuser: bool = False
) -> str:
    """Create a JWT access token.

    Args:
        subject: Token subject (typically user ID)
        expires_delta: Optional token expiration time
        is_superuser: Whether the user is a superuser

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "is_superuser": is_superuser
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

"""
Hashing utilities.
"""

import hashlib

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_url(url: str) -> str:
    """Generate SHA-256 hash of a URL for quick lookups."""
    return hashlib.sha256(url.encode()).hexdigest()

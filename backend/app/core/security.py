from cryptography.fernet import Fernet
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional

from app.infrastructure.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def encrypt_token(token: str) -> bytes:
    if not token:
        return None
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(token.encode())

def decrypt_token(encrypted_token: Optional[bytes]) -> Optional[str]:
    if not encrypted_token:
        return None
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_token).decode()

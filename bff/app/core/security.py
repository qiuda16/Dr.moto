from datetime import datetime, timedelta, timezone
from typing import Optional, Iterable
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import settings
from ..schemas.auth import TokenData, User

# Password Hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "staff")
        email: str = payload.get("email")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role, email=email)
    except JWTError:
        raise credentials_exception
    
    # In a real app, we would query the DB here.
    # For MVP, we'll return a mock user object.
    user = User(
        username=token_data.username,
        email=token_data.email or f"{token_data.username}@example.com",
        role=token_data.role or "staff",
        disabled=False
    )
    return user


def require_roles(allowed_roles: Iterable[str]):
    allowed = {role.strip().lower() for role in allowed_roles}

    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.disabled:
            raise HTTPException(status_code=403, detail="User is disabled")
        user_role = (current_user.role or "").lower()
        if user_role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return dependency

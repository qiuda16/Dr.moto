from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..core.security import create_access_token, get_password_hash, verify_password
from ..core.config import settings
from ..core.rate_limit import check_rate_limit
from ..schemas.auth import Token, UserInDB
import logging

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("bff")


def _admin_user() -> UserInDB:
    hashed = settings.ADMIN_PASSWORD_HASH
    if not hashed:
        hashed = get_password_hash(settings.ADMIN_PASSWORD)
        if settings.is_production and settings.ADMIN_PASSWORD == "change_me_now":
            logger.warning("Production mode with default admin password; update ADMIN_PASSWORD immediately.")
    return UserInDB(
        username=settings.ADMIN_USERNAME,
        hashed_password=hashed,
        email=settings.ADMIN_EMAIL,
        role=settings.ADMIN_ROLE,
        disabled=False,
    )

@router.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    client_ip = request.client.host if request and request.client else "unknown"
    allowed = check_rate_limit(
        "login",
        client_ip,
        settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please retry later.",
        )

    user = _admin_user()
    if form_data.username != user.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "email": user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

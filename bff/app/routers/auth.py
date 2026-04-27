from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.security import create_access_token, get_password_hash, verify_password
from ..core.config import settings
from ..core.db import get_db
from ..core.rate_limit import check_rate_limit
from ..schemas.auth import Token, UserInDB
from ..models import StaffAccount
import logging

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("bff")

DEFAULT_STAFF_ACCOUNTS = (
    {"username": "fzy", "password": "3579", "role": "admin"},
    {"username": "yjk", "password": "3579", "role": "admin"},
    {"username": "sqy", "password": "3579", "role": "admin"},
)


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


def _get_account_from_db(db: Session, username: str) -> UserInDB | None:
    stmt = select(StaffAccount).where(StaffAccount.username == username)
    account = db.execute(stmt).scalars().first()
    if not account:
        return None
    return UserInDB(
        username=account.username,
        hashed_password=account.hashed_password,
        email=account.email,
        role=account.role or "staff",
        disabled=account.disabled,
    )


def ensure_seed_staff_accounts(db: Session) -> None:
    for item in DEFAULT_STAFF_ACCOUNTS:
        stmt = select(StaffAccount).where(StaffAccount.username == item["username"])
        account = db.execute(stmt).scalars().first()
        hashed_password = get_password_hash(item["password"])
        if account is None:
            db.add(
                StaffAccount(
                    username=item["username"],
                    hashed_password=hashed_password,
                    email=f'{item["username"]}@drmoto.local',
                    role=item["role"],
                    disabled=False,
                )
            )
        else:
            account.hashed_password = hashed_password
            account.email = account.email or f'{item["username"]}@drmoto.local'
            account.role = item["role"]
            account.disabled = False
    db.commit()


def _login_rate_limit_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "") if request else ""
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip
    real_ip = request.headers.get("x-real-ip", "") if request else ""
    if real_ip.strip():
        return real_ip.strip()
    return request.client.host if request and request.client else "unknown"

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = _login_rate_limit_identifier(request)
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

    user = _get_account_from_db(db, form_data.username) or _admin_user()
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

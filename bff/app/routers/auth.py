from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..core.security import create_access_token, get_password_hash, verify_password
from ..core.config import settings
from ..schemas.auth import Token, UserInDB

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Mock User DB (MVP)
# password is "secret"
fake_users_db = {
    "staff": {
        "username": "staff",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$Zizl3HsP4XwPgZBy7v2/9w$7aUkK3Ueu4PmgMBgTahNUebWTCdzSWrPgCLRuJx9jcw",
        "email": "staff@drmoto.com",
        "disabled": False,
    }
}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = UserInDB(**user_dict)
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = "staff"
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str


class StaffAccountCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str = "staff"
    disabled: bool = False

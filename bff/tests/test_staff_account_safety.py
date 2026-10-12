import asyncio
import os
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.core.config import settings
from app.models import StaffAccount
from app.routers import auth
from app.schemas.auth import UserInDB


def test_production_never_seeds_demo_accounts(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "prod")
    db = Mock()
    auth.ensure_seed_staff_accounts(db)
    assert not db.mock_calls


def test_seed_preserves_existing_account(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    engine = create_engine("sqlite://")
    StaffAccount.__table__.create(engine)
    with Session(engine) as db:
        db.add(StaffAccount(username="fzy", hashed_password="changed-hash",
                            role="staff", disabled=True))
        db.commit()
        auth.ensure_seed_staff_accounts(db)
        account = db.scalar(select(StaffAccount).where(StaffAccount.username == "fzy"))
        assert account.hashed_password == "changed-hash"
        assert account.role == "staff"
        assert account.disabled is True
    engine.dispose()


def test_disabled_staff_cannot_receive_token(monkeypatch):
    monkeypatch.setattr(auth, "check_rate_limit", lambda *args: True)
    monkeypatch.setattr(auth, "_get_account_from_db", lambda *args: UserInDB(
        username="disabled", hashed_password="hash", role="staff", disabled=True))
    monkeypatch.setattr(auth, "verify_password", lambda *args: True)
    token = Mock()
    monkeypatch.setattr(auth, "create_access_token", token)
    request = Mock(headers={}, client=Mock(host="127.0.0.1"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.login_for_access_token(
            request, Mock(username="disabled", password="correct"), Mock()))
    assert exc.value.status_code == 401
    token.assert_not_called()

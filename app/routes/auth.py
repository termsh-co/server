from __future__ import annotations

import io
import base64

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {"str_strip_whitespace": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = Field(default=None, min_length=6, max_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_png_base64: str


class TotpEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TotpDisableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


def _verify_totp(user: User, code: str | None) -> None:
    if not user.totp_enabled:
        return
    if not code or not user.totp_secret:
        raise HTTPException(status_code=401, detail="2FA kodu gerekli")
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail="Geçersiz 2FA kodu")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Parola en az 8 karakter olmalı")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-posta veya parola hatalı")

    _verify_totp(user, body.totp_code)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh(request: Request, refresh_body: RefreshRequest) -> TokenResponse:
    payload = decode_token(refresh_body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token gerekli")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "totp_enabled": user.totp_enabled,
    }


@router.post("/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TotpSetupResponse:
    secret = pyotp.random_base32()
    result = await db.execute(select(User).where(User.id == user.id))
    row = result.scalar_one()
    row.totp_secret = secret
    row.totp_enabled = False
    await db.commit()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name="termsh")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return TotpSetupResponse(
        secret=secret,
        otpauth_uri=uri,
        qr_png_base64=base64.b64encode(buf.getvalue()).decode("ascii"),
    )


@router.post("/totp/enable")
async def totp_enable(
    body: TotpEnableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.id == user.id))
    row = result.scalar_one()
    if not row.totp_secret:
        raise HTTPException(status_code=400, detail="Önce /auth/totp/setup çağırın")
    totp = pyotp.TOTP(row.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Geçersiz kod")
    row.totp_enabled = True
    await db.commit()
    return {"totp_enabled": True}


@router.post("/totp/disable")
async def totp_disable(
    body: TotpDisableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.id == user.id))
    row = result.scalar_one()
    if not row.totp_enabled or not row.totp_secret:
        raise HTTPException(status_code=400, detail="2FA etkin değil")
    totp = pyotp.TOTP(row.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Geçersiz kod")
    row.totp_enabled = False
    row.totp_secret = None
    await db.commit()
    return {"totp_enabled": False}

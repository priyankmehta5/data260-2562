"""JWT bearer authentication and role dependencies for HW7."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

JWT_SECRET = os.getenv("HW7_JWT_SECRET", "hw7-local-secret-change-in-production")
bearer_scheme = HTTPBearer(auto_error=False)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(subject: str, role: str, expires_in: int = 3600) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(
        json.dumps(
            {"sub": subject, "role": role, "iat": int(time.time()), "exp": int(time.time()) + expires_in},
            separators=(",", ":"),
        ).encode()
    )
    message = f"{header}.{payload}".encode()
    signature = _b64(hmac.new(JWT_SECRET.encode(), message, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(_unb64(payload))
        if int(claims.get("exp", 0)) < int(time.time()):
            raise ValueError("expired token")
        return claims
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid or expired token: {error}"
        ) from error


def find_user(database: Session, username: str):
    normalized = username.strip().lower()
    user = database.query(User).filter(or_(User.username == normalized, User.email == normalized)).first()
    return user


def authenticate_user(database: Session, username: str, password: str):
    user = find_user(database, username)
    if user is None or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return user


def bearer_claims(credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme)) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    return decode_access_token(credentials.credentials)


def get_current_jwt_user(claims: dict[str, Any] = Depends(bearer_claims), database: Session = Depends(get_db)):
    user = database.get(User, int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    def dependency(user=Security(get_current_jwt_user)):
        role = getattr(user, "role", "reader") or "reader"
        if role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dependency

"""Email + password accounts with server-side sessions in an HttpOnly cookie.

Passwords are hashed with scrypt. A session is a random token: the browser
holds it in the cookie, the database holds only its SHA-256 hash, so a leaked
table does not let anyone log in.

Cross-site request forgery: SameSite=Lax cookies are not sent on requests other
sites trigger with POST/PUT/DELETE, and JSON bodies or PUT/DELETE need a CORS
preflight, which this API never grants (the frontend is served from the same origin).
"""
import hashlib
import hmac
import os
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from db import query

COOKIE_NAME = "microbites_session"
# Shared code that unlocks the features that spend API credits. Unset means nobody can unlock.
ACCESS_CODE = os.environ.get("ACCESS_CODE", "")
# Wrong access code attempts allowed per account per window
CODE_ATTEMPTS = 5
CODE_WINDOW = timedelta(minutes=10)
SESSION_DAYS = 30
# Set COOKIE_SECURE=true when serving over HTTPS so the cookie is never sent in plain text
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

SCRYPT_PARAMS = dict(n=2**14, r=8, p=1, dklen=64)

router = APIRouter(prefix="/auth")


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AccessCode(BaseModel):
    code: str = Field(min_length=1, max_length=200)


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT_PARAMS)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    _, salt_hex, digest_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT_PARAMS)
    return hmac.compare_digest(digest.hex(), digest_hex)


# Compared against when an email is unknown, so failed logins take the same time either way
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(response, user_id):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    query("delete from user_session where expires_at < now()")
    query(
        "insert into user_session (token_hash, user_id, expires_at) values (%s, %s, %s)",
        [token_hash(token), user_id, expires],
    )
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=SESSION_DAYS * 24 * 3600, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/",
    )


def current_user(session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    """Dependency for endpoints that need a logged-in user."""
    if session:
        rows = query(
            """
            select u.id, u.email, u.has_access from user_session s join app_user u on u.id = s.user_id
            where s.token_hash = %s and s.expires_at > now()
            """,
            [token_hash(session)],
        )
        if rows:
            return rows[0]
    raise HTTPException(status_code=401, detail="Not logged in")


def user_with_access(user=Depends(current_user)):
    """Dependency for endpoints that spend API credits: requires an unlocked account."""
    if not user["has_access"]:
        raise HTTPException(status_code=403, detail="Access code required")
    return user


@router.post("/register")
def register(credentials: Credentials, response: Response):
    email = credentials.email.lower()
    rows = query(
        "insert into app_user (email, password_hash) values (%s, %s) on conflict (email) do nothing returning id, email, has_access",
        [email, hash_password(credentials.password)],
    )
    if not rows:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    start_session(response, rows[0]["id"])
    return rows[0]


@router.post("/login")
def login(credentials: Credentials, response: Response):
    rows = query("select id, email, has_access, password_hash from app_user where email = %s", [credentials.email.lower()])
    user = rows[0] if rows else None
    if not verify_password(credentials.password, user["password_hash"] if user else DUMMY_HASH) or not user:
        raise HTTPException(status_code=401, detail="Wrong email or password")
    start_session(response, user["id"])
    return {"id": user["id"], "email": user["email"], "has_access": user["has_access"]}


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if session:
        query("delete from user_session where token_hash = %s", [token_hash(session)])
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user=Depends(current_user)):
    return user


# Recent wrong code attempts per user id. In memory: fine for a single server process,
# and a restart only resets the limit.
code_attempts = defaultdict(list)


@router.post("/access-code")
def redeem_access_code(body: AccessCode, user=Depends(current_user)):
    if user["has_access"]:
        return user

    now = datetime.now(timezone.utc)
    attempts = [t for t in code_attempts[user["id"]] if now - t < CODE_WINDOW]
    code_attempts[user["id"]] = attempts
    if len(attempts) >= CODE_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many wrong codes. Try again in a few minutes.")

    if not ACCESS_CODE or not hmac.compare_digest(body.code.strip().encode(), ACCESS_CODE.encode()):
        attempts.append(now)
        raise HTTPException(status_code=400, detail="That access code isn't valid")

    code_attempts.pop(user["id"], None)
    query("update app_user set has_access = true where id = %s", [user["id"]])
    return {**user, "has_access": True}

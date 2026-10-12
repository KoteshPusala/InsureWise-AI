import os
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import db

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "insurewise-ai-secret-key-change-in-production-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7


def create_jwt_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_EXPIRATION_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def extract_user_id_from_token(token_str: str) -> Optional[str]:
    if not token_str:
        return None
    token = token_str.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    if token.startswith("tok_"):
        return token.replace("tok_", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        # Fallback if raw uuid
        if len(token) == 36 and "-" in token:
            return token
        return None


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
def signup(req: SignupRequest):
    name = req.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    existing = db.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please log in.")

    user = db.create_user(name=name, email=req.email, password=req.password)
    token = create_jwt_token(user["id"], user["email"])
    return {
        "user": user,
        "token": token,
        "message": "Account created successfully"
    }


@router.post("/login")
def login(req: LoginRequest):
    user = db.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not db.verify_password(user.get("password_hash", ""), req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_jwt_token(user["id"], user["email"])
    user_data = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "created_at": user.get("created_at", "")
    }
    return {
        "user": user_data,
        "token": token,
        "message": "Logged in successfully"
    }


@router.get("/me")
def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
):
    uid = None
    if authorization:
        uid = extract_user_id_from_token(authorization)
    if not uid and x_user_id:
        uid = extract_user_id_from_token(x_user_id)

    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = db.get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    return {"user": user}

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import db

router = APIRouter(prefix="/auth", tags=["auth"])


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
    # Simple frictionless token for now (no email verification barrier required)
    token = f"tok_{user['id']}"
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

    token = f"tok_{user['id']}"
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
def get_current_user(x_user_id: Optional[str] = Header(None)):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Clean token prefix if sent
    uid = x_user_id.replace("tok_", "")
    user = db.get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User session not found")
    return {"user": user}

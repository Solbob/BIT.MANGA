import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from database import database, get_user_by_email

router = APIRouter()
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-before-deploy")
JWT_ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(LoginRequest):
    pass


class LoginResponse(BaseModel):
    email: str
    token: str
    role: str


def issue_token(user_id: int, role: str) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@router.post("/auth/register", response_model=LoginResponse, status_code=201)
async def register(payload: RegisterRequest):
    password_hash = bcrypt.hashpw(
        payload.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    try:
        user_id = await database.fetch_val(
            """
            INSERT INTO users (email, password_hash, password, role)
            VALUES (:email, :password_hash, :password_hash, 'free')
            RETURNING id
            """,
            {"email": payload.email.lower(), "password_hash": password_hash},
        )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Email is already registered")
        raise
    return LoginResponse(
        email=payload.email.lower(), token=issue_token(user_id, "free"), role="free"
    )


@router.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    user = await get_user_by_email(payload.email.lower())

    if user is None or not bcrypt.checkpw(
        payload.password.encode("utf-8"), user["password_hash"].encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await database.execute(
        "UPDATE users SET last_active_at = NOW() WHERE id = :id",
        {"id": user["id"]},
    )
    return LoginResponse(
        email=user["email"], token=issue_token(user["id"], user["role"]), role=user["role"]
    )


@router.post("/auth/logout")
async def logout():
    return {"message": "Logged out"}

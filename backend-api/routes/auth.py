import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from database import database, get_user_by_email

router = APIRouter()
auth_bearer = HTTPBearer(auto_error=False)
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


class LogoutResponse(BaseModel):
    message: str


def issue_token(user_id: int, role: str, token_version: int = 0) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "ver": token_version,
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
        user = await database.fetch_one(
            """
            INSERT INTO users (email, password_hash, password, role)
            VALUES (:email, :password_hash, :password_hash, 'free')
            RETURNING id, token_version
            """,
            {"email": payload.email.lower(), "password_hash": password_hash},
        )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Email is already registered")
        raise
    return LoginResponse(
        email=payload.email.lower(),
        token=issue_token(user["id"], "free", user["token_version"]),
        role="free",
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
        email=user["email"],
        token=issue_token(user["id"], user["role"], user["token_version"]),
        role=user["role"],
    )


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_bearer),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        claims = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        user_id = int(claims["sub"])
        token_version = int(claims.get("ver", 0))
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    revoked_user = await database.fetch_val(
        """
        UPDATE users SET token_version = token_version + 1
        WHERE id = :id AND token_version = :token_version
        RETURNING id
        """,
        {"id": user_id, "token_version": token_version},
    )
    if revoked_user is None:
        raise HTTPException(status_code=401, detail="Token is already revoked")
    return LogoutResponse(message="Logged out")

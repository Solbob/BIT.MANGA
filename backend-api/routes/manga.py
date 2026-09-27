import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from database import database, get_user_by_id
from routes.auth import JWT_ALGORITHM, JWT_SECRET

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


class SeriesInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=8000)
    cover_image: str = Field(default="", max_length=2000)
    is_premium: bool = False


class ChapterInput(BaseModel):
    series_id: int = Field(gt=0)
    number: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    content: list[str] = Field(min_length=1, max_length=100)


class ChapterUpdate(BaseModel):
    number: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    content: list[str] = Field(min_length=1, max_length=100)


class BookmarkInput(BaseModel):
    series_id: int = Field(gt=0)
    last_read_chapter_id: Optional[int] = Field(default=None, gt=0)


class SeriesResponse(BaseModel):
    id: int
    title: str
    description: str
    cover_image: str
    is_premium: bool
    chapter_count: int = 0


class ChapterSummaryResponse(BaseModel):
    id: int
    series_id: int
    number: int
    title: str
    created_at: datetime


class ChapterResponse(ChapterSummaryResponse):
    content: list[str]


class BookmarkResponse(BaseModel):
    id: int
    series_id: int
    last_read_chapter_id: Optional[int] = None
    updated_at: datetime
    title: Optional[str] = None
    cover_image: Optional[str] = None
    is_premium: Optional[bool] = None
    last_read_chapter_number: Optional[int] = None
    last_read_chapter_title: Optional[str] = None


class SubscriptionResponse(BaseModel):
    status: Literal["active", "expired", "cancelled"]
    started_at: datetime
    expires_at: datetime


class UserResponse(BaseModel):
    id: int
    email: str
    role: Literal["admin", "free", "premium"]
    created_at: datetime
    subscription: Optional[SubscriptionResponse] = None


class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    status: Literal["pending", "success", "failed"]
    created_at: datetime


class CheckoutResponse(BaseModel):
    transaction: TransactionResponse
    role: Literal["premium"]


class RevenuePoint(BaseModel):
    month: str
    mrr: float


class SignupPoint(BaseModel):
    month: str
    free: int
    premium: int
    admin: int


class TransactionPoint(BaseModel):
    month: str
    transaction_count: int
    transaction_volume: float


class AdminMetricsResponse(BaseModel):
    active_users: int
    total_users: int
    premium_users: int
    conversion_rate: float
    transaction_count: int
    transaction_volume: float
    active_subscriptions: int
    projected_mrr: float
    projected_arr: float
    mrr_trend: list[RevenuePoint]
    signups_by_tier: list[SignupPoint]
    transaction_trend: list[TransactionPoint]
    as_of: datetime


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "free", "premium"] = "free"


class AdminUserUpdate(BaseModel):
    email: EmailStr
    role: Literal["admin", "free", "premium"]
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class AdminUserResponse(BaseModel):
    id: int
    email: str
    role: Literal["admin", "free", "premium"]
    created_at: datetime
    last_active_at: datetime
    subscription_status: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None


async def get_current_user_with_role(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
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
    await database.execute(
        """
        UPDATE subscriptions SET status = 'expired'
        WHERE user_id = :user_id AND status = 'active' AND expires_at <= NOW()
        """,
        {"user_id": user_id},
    )
    await database.execute(
        """
        UPDATE users SET role = 'free'
        WHERE id = :user_id AND role = 'premium'
          AND NOT EXISTS (
              SELECT 1 FROM subscriptions
              WHERE user_id = :user_id AND status = 'active' AND expires_at > NOW()
          )
        """,
        {"user_id": user_id},
    )
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    if user["token_version"] != token_version:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")
    await database.execute(
        "UPDATE users SET last_active_at = NOW() WHERE id = :id", {"id": user_id}
    )
    return dict(user)


def require_roles(*roles):
    async def role_dependency(user=Depends(get_current_user_with_role)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_dependency


def serialize_series(row):
    result = dict(row)
    result["id"] = int(result["id"])
    result["chapter_count"] = int(result.get("chapter_count", 0))
    return result


def serialize_chapter(row, include_content=True):
    result = dict(row)
    result["id"] = int(result["id"])
    result["series_id"] = int(result["series_id"])
    if not include_content:
        result.pop("content", None)
    if include_content:
        try:
            result["content"] = json.loads(result["content"])
        except (TypeError, json.JSONDecodeError):
            result["content"] = []
    return result


@router.get("/series", response_model=list[SeriesResponse])
async def list_series(user=Depends(get_current_user_with_role)):
    rows = await database.fetch_all(
        """
        SELECT s.id, s.title, s.description, s.cover_image, s.is_premium,
               COUNT(c.id) AS chapter_count
        FROM series s LEFT JOIN chapters c ON c.series_id = s.id
        GROUP BY s.id ORDER BY s.created_at DESC, s.id DESC
        """
    )
    return [serialize_series(row) for row in rows]


@router.post("/series", response_model=SeriesResponse, status_code=201)
async def create_series(payload: SeriesInput, user=Depends(require_roles("admin"))):
    try:
        row = await database.fetch_one(
            """
            INSERT INTO series (title, description, cover_image, is_premium)
            VALUES (:title, :description, :cover_image, :is_premium)
            RETURNING id, title, description, cover_image, is_premium
            """,
            payload.model_dump(),
        )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Series title already exists")
        raise
    return dict(row)


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(series_id: int, user=Depends(get_current_user_with_role)):
    row = await database.fetch_one(
        """
        SELECT s.id, s.title, s.description, s.cover_image, s.is_premium,
               COUNT(c.id) AS chapter_count
        FROM series s LEFT JOIN chapters c ON c.series_id = s.id
        WHERE s.id = :id GROUP BY s.id
        """,
        {"id": series_id},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Series not found")
    return serialize_series(row)


@router.patch("/series/{series_id}", response_model=SeriesResponse)
async def update_series(
    series_id: int,
    payload: SeriesInput,
    user=Depends(require_roles("admin")),
):
    row = await database.fetch_one(
        """
        UPDATE series SET title = :title, description = :description,
            cover_image = :cover_image, is_premium = :is_premium
        WHERE id = :id
        RETURNING id, title, description, cover_image, is_premium
        """,
        {**payload.model_dump(), "id": series_id},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Series not found")
    return dict(row)


@router.delete("/series/{series_id}", status_code=204)
async def delete_series(series_id: int, user=Depends(require_roles("admin"))):
    deleted = await database.fetch_val(
        "DELETE FROM series WHERE id = :id RETURNING id", {"id": series_id}
    )
    if deleted is None:
        raise HTTPException(status_code=404, detail="Series not found")


@router.get("/series/{series_id}/chapters", response_model=list[ChapterSummaryResponse])
async def list_chapters(series_id: int, user=Depends(get_current_user_with_role)):
    series = await database.fetch_one(
        "SELECT id, is_premium FROM series WHERE id = :id", {"id": series_id}
    )
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    rows = await database.fetch_all(
        """
        SELECT id, series_id, number, title, created_at, content
        FROM chapters WHERE series_id = :series_id ORDER BY number
        """,
        {"series_id": series_id},
    )
    return [serialize_chapter(row, include_content=False) for row in rows]


@router.post("/chapters", response_model=ChapterResponse, status_code=201)
async def create_chapter(payload: ChapterInput, user=Depends(require_roles("admin"))):
    row = await database.fetch_one(
        """
        INSERT INTO chapters (series_id, number, title, content)
        VALUES (:series_id, :number, :title, :content)
        RETURNING id, series_id, number, title, content, created_at
        """,
        {**payload.model_dump(exclude={"content"}), "content": json.dumps(payload.content)},
    )
    return serialize_chapter(row)


@router.get("/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(chapter_id: int, user=Depends(get_current_user_with_role)):
    row = await database.fetch_one(
        """
        SELECT c.id, c.series_id, c.number, c.title, c.content, c.created_at,
               s.is_premium
        FROM chapters c JOIN series s ON s.id = c.series_id WHERE c.id = :id
        """,
        {"id": chapter_id},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if row["is_premium"] and user["role"] not in ("premium", "admin"):
        raise HTTPException(status_code=403, detail="Premium membership required")
    result = serialize_chapter(row)
    result.pop("is_premium", None)
    return result


@router.patch("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    payload: ChapterUpdate,
    user=Depends(require_roles("admin")),
):
    row = await database.fetch_one(
        """
        UPDATE chapters SET number = :number, title = :title, content = :content
        WHERE id = :id
        RETURNING id, series_id, number, title, content, created_at
        """,
        {
            **payload.model_dump(exclude={"content"}),
            "content": json.dumps(payload.content),
            "id": chapter_id,
        },
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return serialize_chapter(row)


@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter(chapter_id: int, user=Depends(require_roles("admin"))):
    deleted = await database.fetch_val(
        "DELETE FROM chapters WHERE id = :id RETURNING id", {"id": chapter_id}
    )
    if deleted is None:
        raise HTTPException(status_code=404, detail="Chapter not found")


async def validate_bookmark_chapter(series_id, chapter_id):
    if chapter_id is None:
        return
    row = await database.fetch_one(
        "SELECT id FROM chapters WHERE id = :chapter_id AND series_id = :series_id",
        {"chapter_id": chapter_id, "series_id": series_id},
    )
    if row is None:
        raise HTTPException(status_code=422, detail="Chapter does not belong to this series")


@router.get("/bookmarks", response_model=list[BookmarkResponse])
async def list_bookmarks(user=Depends(get_current_user_with_role)):
    rows = await database.fetch_all(
        """
        SELECT b.id, b.series_id, b.last_read_chapter_id, b.updated_at,
               s.title, s.cover_image, s.is_premium,
               c.number AS last_read_chapter_number, c.title AS last_read_chapter_title
        FROM bookmarks b JOIN series s ON s.id = b.series_id
        LEFT JOIN chapters c ON c.id = b.last_read_chapter_id
        WHERE b.user_id = :user_id ORDER BY b.updated_at DESC
        """,
        {"user_id": user["id"]},
    )
    return [dict(row) for row in rows]


@router.post("/bookmarks", response_model=BookmarkResponse, status_code=201)
async def upsert_bookmark(payload: BookmarkInput, user=Depends(get_current_user_with_role)):
    series = await database.fetch_one(
        "SELECT id FROM series WHERE id = :id", {"id": payload.series_id}
    )
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    await validate_bookmark_chapter(payload.series_id, payload.last_read_chapter_id)
    existing = await database.fetch_one(
        "SELECT id FROM bookmarks WHERE user_id = :user_id AND series_id = :series_id",
        {"user_id": user["id"], "series_id": payload.series_id},
    )
    if existing is None and user["role"] == "free":
        count = await database.fetch_val(
            "SELECT COUNT(*) FROM bookmarks WHERE user_id = :user_id",
            {"user_id": user["id"]},
        )
        if count >= 20:
            raise HTTPException(status_code=403, detail="Free accounts can save up to 20 series")
    row = await database.fetch_one(
        """
        INSERT INTO bookmarks (user_id, series_id, last_read_chapter_id, updated_at)
        VALUES (:user_id, :series_id, :chapter_id, NOW())
        ON CONFLICT (user_id, series_id) DO UPDATE SET
            last_read_chapter_id = COALESCE(EXCLUDED.last_read_chapter_id, bookmarks.last_read_chapter_id),
            updated_at = NOW()
        RETURNING id, series_id, last_read_chapter_id, updated_at
        """,
        {
            "user_id": user["id"],
            "series_id": payload.series_id,
            "chapter_id": payload.last_read_chapter_id,
        },
    )
    return dict(row)


@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    payload: BookmarkInput,
    user=Depends(get_current_user_with_role),
):
    await validate_bookmark_chapter(payload.series_id, payload.last_read_chapter_id)
    row = await database.fetch_one(
        """
        UPDATE bookmarks SET last_read_chapter_id = :chapter_id, updated_at = NOW()
        WHERE id = :id AND user_id = :user_id AND series_id = :series_id
        RETURNING id, series_id, last_read_chapter_id, updated_at
        """,
        {
            "id": bookmark_id,
            "user_id": user["id"],
            "series_id": payload.series_id,
            "chapter_id": payload.last_read_chapter_id,
        },
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return dict(row)


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(bookmark_id: int, user=Depends(get_current_user_with_role)):
    deleted = await database.fetch_val(
        "DELETE FROM bookmarks WHERE id = :id AND user_id = :user_id RETURNING id",
        {"id": bookmark_id, "user_id": user["id"]},
    )
    if deleted is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")


@router.post("/checkout/mock", response_model=CheckoutResponse)
async def mock_checkout(user=Depends(get_current_user_with_role)):
    if user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin accounts do not need a subscription")
    async with database.transaction():
        transaction = await database.fetch_one(
            """
            INSERT INTO transactions (user_id, amount, method, status)
            VALUES (:user_id, :amount, 'mock_checkout', 'success')
            RETURNING id, amount, status, created_at
            """,
            {"user_id": user["id"], "amount": Decimal("9.99")},
        )
        await database.execute(
            """
            INSERT INTO subscriptions (user_id, status, started_at, expires_at)
            VALUES (:user_id, 'active', NOW(), NOW() + INTERVAL '30 days')
            ON CONFLICT (user_id) DO UPDATE SET
                status = 'active', started_at = NOW(), expires_at = NOW() + INTERVAL '30 days'
            """,
            {"user_id": user["id"]},
        )
        await database.execute(
            "UPDATE users SET role = 'premium' WHERE id = :user_id",
            {"user_id": user["id"]},
        )
    return {"transaction": dict(transaction), "role": "premium"}


@router.get("/users/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_user_with_role)):
    subscription = await database.fetch_one(
        """
        SELECT status, started_at, expires_at FROM subscriptions
        WHERE user_id = :user_id ORDER BY started_at DESC LIMIT 1
        """,
        {"user_id": user["id"]},
    )
    result = dict(user)
    result.pop("token_version", None)
    result["subscription"] = dict(subscription) if subscription else None
    return result


@router.get("/admin/users", response_model=list[AdminUserResponse])
async def admin_list_users(
    search: str = Query(default="", max_length=255),
    limit: int = Query(default=200, ge=1, le=500),
    user=Depends(require_roles("admin")),
):
    term = search.strip()
    rows = await database.fetch_all(
        """
        SELECT u.id, u.email, u.role, u.created_at, u.last_active_at,
               s.status AS subscription_status, s.expires_at AS subscription_expires_at
        FROM users u LEFT JOIN subscriptions s ON s.user_id = u.id
        WHERE (:search = '' OR u.email ILIKE :pattern OR CAST(u.id AS TEXT) ILIKE :pattern)
        ORDER BY u.created_at DESC, u.id DESC LIMIT :limit
        """,
        {"search": term, "pattern": f"%{term}%", "limit": limit},
    )
    return [dict(row) for row in rows]


@router.post("/admin/users", response_model=AdminUserResponse, status_code=201)
async def admin_create_user(
    payload: AdminUserCreate, user=Depends(require_roles("admin"))
):
    email = str(payload.email).lower()
    password_hash = bcrypt.hashpw(
        payload.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    try:
        async with database.transaction():
            row = await database.fetch_one(
                """
                INSERT INTO users (email, password_hash, password, role)
                VALUES (:email, :password_hash, :password_hash, :role)
                RETURNING id, email, role, created_at, last_active_at
                """,
                {"email": email, "password_hash": password_hash, "role": payload.role},
            )
            if payload.role == "premium":
                await database.execute(
                    """
                    INSERT INTO subscriptions (user_id, status, expires_at)
                    VALUES (:user_id, 'active', NOW() + INTERVAL '30 days')
                    """,
                    {"user_id": row["id"]},
                )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Email is already registered")
        raise
    result = dict(row)
    result["subscription_status"] = "active" if payload.role == "premium" else None
    result["subscription_expires_at"] = None
    if payload.role == "premium":
        result["subscription_expires_at"] = await database.fetch_val(
            "SELECT expires_at FROM subscriptions WHERE user_id = :user_id",
            {"user_id": row["id"]},
        )
    return result


@router.patch("/admin/users/{user_id}", response_model=AdminUserResponse)
async def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    user=Depends(require_roles("admin")),
):
    if user_id == int(user["id"]):
        raise HTTPException(status_code=400, detail="You cannot edit your own account here")

    email = str(payload.email).lower()
    password_hash = None
    if payload.password is not None:
        password_hash = bcrypt.hashpw(
            payload.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    try:
        async with database.transaction():
            await database.execute("SELECT pg_advisory_xact_lock(74102026)")
            current = await database.fetch_one(
                "SELECT id, role FROM users WHERE id = :id FOR UPDATE",
                {"id": user_id},
            )
            if current is None:
                raise HTTPException(status_code=404, detail="User not found")
            if current["role"] == "admin" and payload.role != "admin":
                admin_count = await database.fetch_val(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin'"
                )
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=400, detail="The last admin cannot be demoted"
                    )

            row = await database.fetch_one(
                """
                UPDATE users SET email = :email, role = :role,
                    password_hash = COALESCE(:password_hash, password_hash),
                    password = COALESCE(:password_hash, password),
                    token_version = token_version + 1
                WHERE id = :id
                RETURNING id, email, role, created_at, last_active_at
                """,
                {
                    "id": user_id,
                    "email": email,
                    "role": payload.role,
                    "password_hash": password_hash,
                },
            )

            if payload.role == "premium":
                active_subscription = await database.fetch_val(
                    """
                    SELECT user_id FROM subscriptions
                    WHERE user_id = :user_id AND status = 'active' AND expires_at > NOW()
                    """,
                    {"user_id": user_id},
                )
                if active_subscription is None:
                    await database.execute(
                        """
                        INSERT INTO subscriptions (user_id, status, started_at, expires_at)
                        VALUES (:user_id, 'active', NOW(), NOW() + INTERVAL '30 days')
                        ON CONFLICT (user_id) DO UPDATE SET
                            status = 'active', started_at = NOW(),
                            expires_at = NOW() + INTERVAL '30 days'
                        """,
                        {"user_id": user_id},
                    )
            else:
                await database.execute(
                    """
                    UPDATE subscriptions SET status = 'cancelled', expires_at = NOW()
                    WHERE user_id = :user_id AND status = 'active'
                    """,
                    {"user_id": user_id},
                )
            subscription = await database.fetch_one(
                "SELECT status, expires_at FROM subscriptions WHERE user_id = :user_id",
                {"user_id": user_id},
            )
    except HTTPException:
        raise
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Email is already registered")
        raise

    result = dict(row)
    result["subscription_status"] = subscription["status"] if subscription else None
    result["subscription_expires_at"] = subscription["expires_at"] if subscription else None
    return result


@router.delete("/admin/users/{user_id}", status_code=204)
async def admin_delete_user(user_id: int, user=Depends(require_roles("admin"))):
    if user_id == int(user["id"]):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    async with database.transaction():
        await database.execute("SELECT pg_advisory_xact_lock(74102026)")
        target = await database.fetch_one(
            "SELECT id, role FROM users WHERE id = :id FOR UPDATE", {"id": user_id}
        )
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        if target["role"] == "admin":
            admin_count = await database.fetch_val(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            )
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="The last admin cannot be deleted")
        await database.execute("DELETE FROM users WHERE id = :id", {"id": user_id})


@router.get("/admin/metrics", response_model=AdminMetricsResponse)
async def admin_metrics(user=Depends(require_roles("admin"))):
    users = await database.fetch_one(
        """
        SELECT COUNT(*) AS total_users,
               COUNT(*) FILTER (WHERE last_active_at >= NOW() - INTERVAL '30 days') AS active_users,
               COUNT(*) FILTER (WHERE role = 'premium') AS premium_users
        FROM users
        """
    )
    transaction = await database.fetch_one(
        """
        SELECT COUNT(*) AS transaction_count,
               COALESCE(SUM(amount), 0) AS transaction_volume
        FROM transactions WHERE status = 'success'
        """
    )
    revenue = await database.fetch_one(
        """
        SELECT COUNT(*) AS active_subscriptions,
               COALESCE(COUNT(*) * 9.99, 0) AS projected_mrr
        FROM subscriptions WHERE status = 'active' AND expires_at > NOW()
        """
    )
    mrr_rows = await database.fetch_all(
        """
        SELECT TO_CHAR(months.month, 'Mon YY') AS month,
               COUNT(s.id) * 9.99 AS mrr
        FROM generate_series(
            date_trunc('month', NOW()) - INTERVAL '5 months',
            date_trunc('month', NOW()), INTERVAL '1 month'
        ) AS months(month)
        LEFT JOIN subscriptions s ON s.status = 'active'
            AND s.started_at <= months.month + INTERVAL '1 month'
            AND s.expires_at > months.month
        GROUP BY months.month ORDER BY months.month
        """
    )
    signup_rows = await database.fetch_all(
        """
        SELECT TO_CHAR(date_trunc('month', created_at), 'Mon YY') AS month,
               COUNT(*) FILTER (WHERE role = 'free') AS free,
               COUNT(*) FILTER (WHERE role = 'premium') AS premium,
               COUNT(*) FILTER (WHERE role = 'admin') AS admin
        FROM users WHERE created_at >= date_trunc('month', NOW()) - INTERVAL '5 months'
        GROUP BY date_trunc('month', created_at) ORDER BY date_trunc('month', created_at)
        """
    )
    transaction_rows = await database.fetch_all(
        """
        SELECT TO_CHAR(months.month, 'Mon YY') AS month,
               COUNT(t.id) AS transaction_count,
               COALESCE(SUM(t.amount), 0) AS transaction_volume
        FROM generate_series(
            date_trunc('month', NOW()) - INTERVAL '5 months',
            date_trunc('month', NOW()), INTERVAL '1 month'
        ) AS months(month)
        LEFT JOIN transactions t ON t.status = 'success'
            AND t.created_at >= months.month
            AND t.created_at < months.month + INTERVAL '1 month'
        GROUP BY months.month ORDER BY months.month
        """
    )
    total_users = int(users["total_users"] or 0)
    premium_users = int(users["premium_users"] or 0)
    projected_mrr = float(revenue["projected_mrr"] or 0)
    return {
        "active_users": int(users["active_users"] or 0),
        "total_users": total_users,
        "premium_users": premium_users,
        "conversion_rate": round(premium_users / total_users * 100, 1) if total_users else 0,
        "transaction_count": int(transaction["transaction_count"] or 0),
        "transaction_volume": float(transaction["transaction_volume"] or 0),
        "active_subscriptions": int(revenue["active_subscriptions"] or 0),
        "projected_mrr": projected_mrr,
        "projected_arr": projected_mrr * 12,
        "mrr_trend": [dict(row) for row in mrr_rows],
        "signups_by_tier": [dict(row) for row in signup_rows],
        "transaction_trend": [dict(row) for row in transaction_rows],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
import asyncio
import json
import os

import bcrypt
from databases import Database

POSTGRES_USER = os.getenv("POSTGRES_USER", "temp")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "temp")
POSTGRES_DB = os.getenv("POSTGRES_DB", "advcompro")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}/{POSTGRES_DB}"
)

database = Database(DATABASE_URL)


async def connect_db():
    for attempt in range(5):
        try:
            await database.connect()
            return
        except Exception:
            if attempt == 4:
                raise
            await asyncio.sleep(2)


async def disconnect_db():
    await database.disconnect()


async def setup_db():
    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role VARCHAR(16) NOT NULL DEFAULT 'free'
                CHECK (role IN ('admin', 'free', 'premium')),
            token_version BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            password TEXT,
            token TEXT,
            create_at TIMESTAMPTZ
        )
        """
    )

    # Upgrade the original ACP users table in place without losing its accounts.
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS id BIGSERIAL")
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
    await database.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(16) DEFAULT 'free'"
    )
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ")
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ")
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password TEXT")
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token TEXT")
    await database.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version BIGINT DEFAULT 0")
    legacy_users = await database.fetch_all(
        """
        SELECT id, password, password_hash FROM users
        WHERE password_hash IS NULL
           OR (password IS NOT NULL AND password IS DISTINCT FROM password_hash)
        """
    )
    for user in legacy_users:
        password_hash = user["password_hash"]
        if not password_hash and user["password"] is not None:
            legacy_password = user["password"].encode("utf-8")
            try:
                if not user["password"].startswith(("$2a$", "$2b$", "$2y$")):
                    raise ValueError("Legacy password is not a bcrypt hash")
                bcrypt.checkpw(b"", legacy_password)
                password_hash = user["password"]
            except ValueError:
                password_hash = bcrypt.hashpw(legacy_password, bcrypt.gensalt()).decode("utf-8")
        if password_hash:
            await database.execute(
                """
                UPDATE users SET password_hash = :password_hash, password = :password_hash
                WHERE id = :id
                """,
                {"id": user["id"], "password_hash": password_hash},
            )
    await database.execute(
        "UPDATE users SET created_at = create_at WHERE created_at IS NULL AND create_at IS NOT NULL"
    )
    await database.execute("UPDATE users SET created_at = NOW() WHERE created_at IS NULL")
    await database.execute("UPDATE users SET token_version = 0 WHERE token_version IS NULL")
    await database.execute(
        "UPDATE users SET last_active_at = created_at WHERE last_active_at IS NULL"
    )
    await database.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users (email)")
    await database.execute(
        """
        DO $$
        DECLARE primary_key_name TEXT;
        DECLARE primary_key_definition TEXT;
        BEGIN
            SELECT conname, pg_get_constraintdef(oid)
            INTO primary_key_name, primary_key_definition
            FROM pg_constraint
            WHERE conrelid = 'users'::regclass AND contype = 'p'
            LIMIT 1;
            IF primary_key_name IS NOT NULL AND primary_key_definition <> 'PRIMARY KEY (id)' THEN
                EXECUTE format('ALTER TABLE users DROP CONSTRAINT %I', primary_key_name);
                ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
            ELSIF primary_key_name IS NULL THEN
                ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
            END IF;
        END $$
        """
    )
    await database.execute("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL")
    await database.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'free'")
    await database.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")
    await database.execute("ALTER TABLE users ALTER COLUMN token_version SET DEFAULT 0")
    await database.execute("ALTER TABLE users ALTER COLUMN token_version SET NOT NULL")
    await database.execute("ALTER TABLE users ALTER COLUMN created_at SET DEFAULT NOW()")
    await database.execute("ALTER TABLE users ALTER COLUMN created_at SET NOT NULL")
    await database.execute("ALTER TABLE users ALTER COLUMN last_active_at SET DEFAULT NOW()")
    await database.execute("ALTER TABLE users ALTER COLUMN last_active_at SET NOT NULL")
    await database.execute(
        """
        DO $$ BEGIN
            ALTER TABLE users ADD CONSTRAINT users_role_check
                CHECK (role IN ('admin', 'free', 'premium'));
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )

    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS series (
            id BIGSERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            cover_image TEXT NOT NULL DEFAULT '',
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS chapters (
            id BIGSERIAL PRIMARY KEY,
            series_id BIGINT NOT NULL REFERENCES series(id) ON DELETE CASCADE,
            number INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(series_id, number)
        )
        """
    )
    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            series_id BIGINT NOT NULL REFERENCES series(id) ON DELETE CASCADE,
            last_read_chapter_id BIGINT REFERENCES chapters(id) ON DELETE SET NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, series_id)
        )
        """
    )
    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status VARCHAR(16) NOT NULL CHECK (status IN ('active', 'expired', 'cancelled')),
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            UNIQUE(user_id)
        )
        """
    )
    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
            method VARCHAR(64) NOT NULL,
            status VARCHAR(16) NOT NULL CHECK (status IN ('pending', 'success', 'failed')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    demo_password = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
    await database.execute(
        """
        INSERT INTO users (email, password_hash, password, role)
        VALUES (:email, :password_hash, :password_hash, 'free')
        ON CONFLICT (email) DO NOTHING
        """,
        {"email": "demo@example.com", "password_hash": demo_password},
    )
    seed_admin_password = os.getenv("SEED_ADMIN_PASSWORD")
    if seed_admin_password:
        admin_password_hash = bcrypt.hashpw(
            seed_admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        await database.execute(
            """
            INSERT INTO users (email, password_hash, password, role)
            VALUES (:email, :password_hash, :password_hash, 'admin')
            ON CONFLICT (email) DO NOTHING
            """,
            {
                "email": os.getenv("SEED_ADMIN_EMAIL", "admin@example.com").lower(),
                "password_hash": admin_password_hash,
            },
        )

    sample_series = [
        {
            "title": "The Last Lantern",
            "description": "A quiet courier carries a dying city's final light through the rain-soaked wilds.",
            "cover_image": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=800&q=85",
            "is_premium": False,
        },
        {
            "title": "Chrome Ronin",
            "description": "In a neon sprawl, a disgraced swordsmith builds one last impossible blade.",
            "cover_image": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=800&q=85",
            "is_premium": True,
        },
        {
            "title": "Blue Hour Cafe",
            "description": "Every night, a tiny cafe serves the people who cannot sleep.",
            "cover_image": "https://images.unsplash.com/photo-1442512595331-e89e73853f31?auto=format&fit=crop&w=800&q=85",
            "is_premium": False,
        },
    ]
    for item in sample_series:
        await database.execute(
            """
            INSERT INTO series (title, description, cover_image, is_premium)
            VALUES (:title, :description, :cover_image, :is_premium)
            ON CONFLICT (title) DO NOTHING
            """,
            item,
        )

    series_rows = await database.fetch_all("SELECT id, title FROM series")
    for series in series_rows:
        pages = [
            "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1400&q=85",
            "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=85",
            "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1400&q=85",
        ]
        await database.execute(
            """
            INSERT INTO chapters (series_id, number, title, content)
            VALUES (:series_id, 1, 'A light in the rain', :content)
            ON CONFLICT (series_id, number) DO NOTHING
            """,
            {"series_id": series["id"], "content": json.dumps(pages)},
        )


async def get_user_by_email(email: str):
    return await database.fetch_one(
        "SELECT id, email, password_hash, role, token_version, created_at FROM users WHERE email = :email",
        {"email": email},
    )


async def get_user_by_id(user_id: int):
    return await database.fetch_one(
        "SELECT id, email, role, token_version, created_at FROM users WHERE id = :id",
        {"id": user_id},
    )

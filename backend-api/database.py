import asyncio
import json
import os
import tempfile
from pathlib import Path

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
_catalog_seed_lock = asyncio.Lock()


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _write_catalog_seed(schema_path: Path, series_rows, chapter_rows) -> None:
    schema_sql = schema_path.read_text(encoding="utf-8")
    start_marker = "-- BEGIN AUTO-GENERATED CATALOG SEED"
    end_marker = "-- END AUTO-GENERATED CATALOG SEED"
    start = schema_sql.find(start_marker)
    end = schema_sql.find(end_marker)
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("Catalog seed markers are missing from schema.sql")

    seed_lines = [start_marker]
    if series_rows:
        values = ",\n".join(
            "    ({}, {}, {}, {})".format(
                _sql_literal(row["title"]),
                _sql_literal(row["description"]),
                _sql_literal(row["cover_image"]),
                "TRUE" if row["is_premium"] else "FALSE",
            )
            for row in series_rows
        )
        seed_lines.extend(
            [
                "INSERT INTO series (title, description, cover_image, is_premium)",
                "VALUES",
                values,
                "ON CONFLICT (title) DO UPDATE SET",
                "    description = EXCLUDED.description,",
                "    cover_image = EXCLUDED.cover_image,",
                "    is_premium = EXCLUDED.is_premium;",
                "-- statement-break",
            ]
        )

    if chapter_rows:
        values = ",\n".join(
            "    ({}, {}, {}, {})".format(
                _sql_literal(row["series_title"]),
                row["number"],
                _sql_literal(row["title"]),
                _sql_literal(row["content"]),
            )
            for row in chapter_rows
        )
        seed_lines.extend(
            [
                "INSERT INTO chapters (series_id, number, title, content)",
                "SELECT series.id, seed.number, seed.title, seed.content",
                "FROM (",
                "    VALUES",
                values,
                ") AS seed(series_title, number, title, content)",
                "JOIN series ON series.title = seed.series_title",
                "ON CONFLICT (series_id, number) DO UPDATE SET",
                "    title = EXCLUDED.title,",
                "    content = EXCLUDED.content;",
                "-- statement-break",
            ]
        )
    seed_lines.append(end_marker)

    updated_schema = (
        schema_sql[:start] + "\n".join(seed_lines) + schema_sql[end + len(end_marker):]
    )
    schema_mode = schema_path.stat().st_mode
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f"{schema_path.name}.", suffix=".tmp", dir=schema_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as temp_file:
            temp_file.write(updated_schema)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_name, schema_mode)
        os.replace(temp_name, schema_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


async def persist_catalog_seed() -> None:
    async with _catalog_seed_lock:
        series_rows = await database.fetch_all(
            """
            SELECT title, description, cover_image, is_premium
            FROM series ORDER BY title
            """
        )
        chapter_rows = await database.fetch_all(
            """
            SELECT s.title AS series_title, c.number, c.title, c.content
            FROM chapters c JOIN series s ON s.id = c.series_id
            ORDER BY s.title, c.number
            """
        )
        schema_path = Path(__file__).with_name("schema.sql")
        await asyncio.to_thread(
            _write_catalog_seed, schema_path, series_rows, chapter_rows
        )


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
    schema_sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    for statement in schema_sql.split("-- statement-break"):
        if statement.strip():
            await database.execute(statement)

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
    await persist_catalog_seed()


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

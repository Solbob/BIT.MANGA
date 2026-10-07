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
);
-- statement-break

-- Upgrade the original ACP users table in place without losing its accounts.
ALTER TABLE users ADD COLUMN IF NOT EXISTS id BIGSERIAL;
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(16) DEFAULT 'free';
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ;
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS password TEXT;
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS token TEXT;
-- statement-break
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version BIGINT DEFAULT 0;
-- statement-break

CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users (email);
-- statement-break

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
END $$;
-- statement-break

CREATE TABLE IF NOT EXISTS series (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    cover_image TEXT NOT NULL DEFAULT '',
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- statement-break

CREATE TABLE IF NOT EXISTS chapters (
    id BIGSERIAL PRIMARY KEY,
    series_id BIGINT NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(series_id, number)
);
-- statement-break

CREATE TABLE IF NOT EXISTS bookmarks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    series_id BIGINT NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    last_read_chapter_id BIGINT REFERENCES chapters(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, series_id)
);
-- statement-break

CREATE TABLE IF NOT EXISTS subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(16) NOT NULL CHECK (status IN ('active', 'expired', 'cancelled')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id)
);
-- statement-break

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    method VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('pending', 'success', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

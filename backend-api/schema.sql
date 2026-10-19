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
-- statement-break

-- BEGIN AUTO-GENERATED CATALOG SEED
INSERT INTO series (title, description, cover_image, is_premium)
VALUES
    ('Blue Hour Cafe', 'Every night, a tiny cafe serves the people who cannot sleep.', 'https://images.unsplash.com/photo-1442512595331-e89e73853f31?auto=format&fit=crop&w=800&q=85', FALSE),
    ('Chrome Ronin', 'In a neon sprawl, a disgraced swordsmith builds one last impossible blade.', 'https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=800&q=85', TRUE),
    ('Kemono Jihen', 'In a remote village, supernatural livestock deaths bring Tokyo detective Kohachi Inugami to investigate. He discovers the ostracized boy Kabane is a half-ghoul, then takes him to Tokyo to join a detective agency handling cases involving hidden supernatural beings. Alongside fellow boys with strange powers, Kabane learns about friendship and his own emotions while searching for his missing parents.', 'https://upload.wikimedia.org/wikipedia/en/2/2d/Kemono_Jihen_1.png?utm_source=en.wikipedia.org&utm_campaign=imageinfo&utm_content=original', FALSE),
    ('Mirai Suenaga Collection', 'Comedy manga about school life', 'https://upload.wikimedia.org/wikipedia/commons/8/8f/Mirai_Suenaga_Fanart_-_7586726230.jpg', FALSE),
    ('Test.series', 'Build for testing database', 'F', FALSE),
    ('The Last Lantern', 'A quiet courier carries a dying city''s final light through the rain-soaked wilds.', 'https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=800&q=85', FALSE),
    ('The Melancholy of Haruhi Suzumiya', 'Kyon expects high school to be ordinary until he meets Haruhi Suzumiya, an energetic girl determined to find aliens, time travelers, and espers. After Haruhi starts the SOS Brigade, Kyon discovers its other members really are extraordinary-and Haruhi herself unknowingly has the power to reshape reality. The group must keep her entertained while preventing her whims from changing the world.', 'https://upload.wikimedia.org/wikipedia/en/1/11/Haruhi_book_01_s.jpg?utm_source=en.wikipedia.org&utm_campaign=index&utm_content=original', FALSE)
ON CONFLICT (title) DO UPDATE SET
    description = EXCLUDED.description,
    cover_image = EXCLUDED.cover_image,
    is_premium = EXCLUDED.is_premium;
-- statement-break
INSERT INTO chapters (series_id, number, title, content)
SELECT series.id, seed.number, seed.title, seed.content
FROM (
    VALUES
    ('Blue Hour Cafe', 1, 'A light in the rain', '["https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1400&q=85", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=85", "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1400&q=85"]'),
    ('Chrome Ronin', 1, 'A light in the rain', '["https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1400&q=85", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=85", "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1400&q=85"]'),
    ('Kemono Jihen', 1, 'Part 1: The Village Case', '["https://static.wikia.nocookie.net/kemonojihen/images/4/42/Inugami_talking_to_Mrs._Kusaka.png/revision/latest?cb=20200619062145", "https://static.wikia.nocookie.net/kemonojihen/images/0/04/Yataro_helps_Inugami.png/revision/latest?cb=20200619062723"]'),
    ('Kemono Jihen', 2, 'Part 2: The Inugami Agency', '["https://placehold.co/512x720/ffffff/111111.png?text=Part+2+-+Placeholder"]'),
    ('Mirai Suenaga Collection', 1, 'Mirai Suenaga', '["https://upload.wikimedia.org/wikipedia/commons/8/8f/Mirai_Suenaga_Fanart_-_7586726230.jpg"]'),
    ('Test.series', 1, 'test chap', '["f"]'),
    ('The Last Lantern', 1, 'A light in the rain', '["https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1400&q=85", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=85", "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1400&q=85"]'),
    ('The Melancholy of Haruhi Suzumiya', 1, 'Placeholder due to copy right reason', '["https://placehold.co/512x720/ffffff/111111.png?text=Blank+Manga+Page"]')
) AS seed(series_title, number, title, content)
JOIN series ON series.title = seed.series_title
ON CONFLICT (series_id, number) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content;
-- statement-break
-- END AUTO-GENERATED CATALOG SEED

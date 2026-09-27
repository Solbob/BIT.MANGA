# BIT.MANGA

A responsive manga reading app built on the supplied ACP boilerplate: Next.js Pages Router, shadcn-style UI components, FastAPI, PostgreSQL, bcrypt password hashes, and JWT authentication.

## Run locally

1. Open a terminal in the repository root (the directory containing `docker-compose.yaml`). Make sure Docker is running.
2. Build and start the website, API, and PostgreSQL database on a standard Docker host:

```bash
docker compose -p bitmanga-local up -d --build
```

In GitHub Codespaces, use the networking override instead:

```bash
docker compose -p bitmanga-local -f docker-compose.yaml -f docker-compose.codespaces.yaml up -d --build
```

3. Wait until PostgreSQL reports `healthy` and the other services report `Up`:

	```bash
	docker compose -p bitmanga-local ps
	```

4. Open the website at `http://localhost:3000`. The API documentation is at `http://localhost:8000/docs`.
5. Sign in with one of the local demo accounts:
	- Reader: `demo@example.com` / `password`
	- Admin: `admin@example.com` / `admin123`
6. To stop the services without deleting the database volume, run:

	```bash
	docker compose -p bitmanga-local stop
	```

For recurring build, startup, or login issues, see the [bug-fix log](bug-fix-log.md) before troubleshooting.

Registration creates Free accounts. The local admin account is seeded only when `SEED_ADMIN_PASSWORD` is set. Compose provides development defaults; replace them along with `JWT_SECRET` for any shared or deployed environment. Serve production traffic through HTTPS at the deployment edge.

## Pages

- `/` — public landing page and Free/Premium overview
- `/login` — sign in and registration
- `/reader` — browse, bookmark, and read chapters; Admins can manage series and chapters
- `/pricing` — tier comparison and mock Premium checkout
- `/profile` — role, membership, bookmarks, and reading history
- `/admin` — Admin-only reader, revenue, conversion, and signup analytics

## API

All application routes are under `/api`. Login and registration return a signed 24-hour JWT. Authenticated requests send it as `Authorization: Bearer <token>`; the Next.js helper attaches it automatically. The API reloads the user role from PostgreSQL, checks ownership, and rejects locked chapter reads itself.

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`
- `GET/POST /api/series`, `GET/PATCH/DELETE /api/series/{id}`
- `GET /api/series/{id}/chapters`, `POST /api/chapters`, `GET/PATCH/DELETE /api/chapters/{id}`
- `GET/POST /api/bookmarks`, `PATCH/DELETE /api/bookmarks/{id}`
- `POST /api/checkout/mock`, `GET /api/users/me`
- `GET /api/admin/metrics` (Admin only)

The initial database setup upgrades the starter's original users table in place and seeds a small demonstration catalog. Password hashes use bcrypt. The checkout is simulated and records a successful transaction and 30-day subscription; it does not collect payment details.

## Data and deployment notes

PostgreSQL stores users, series, chapters, bookmarks, subscriptions, and transactions with foreign keys. Free accounts can save 20 series; Premium and Admin accounts have no bookmark cap. Premium subscriptions expire after 30 days and the API restores the Free role when an expired account next makes an authenticated request.

Configure a strong `JWT_SECRET` and unique `SEED_ADMIN_PASSWORD` outside development. The Compose defaults are for local coursework only. For a TLS-terminated production deployment, point a DNS name at the host and provide production credentials through the shell or an uncommitted `.env` file, then run:

```bash
docker compose -p bitmanga-prod -f docker-compose.yaml -f docker-compose.production.yaml up -d --build
```

Set `PUBLIC_DOMAIN`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET`, and `SEED_ADMIN_PASSWORD` before running the command. Caddy obtains and renews the HTTPS certificate; only ports 80 and 443 are published in this configuration. The production project name keeps its PostgreSQL volume separate from the local development database.

# BIT.MANGA

A responsive manga reading app built on the supplied ACP boilerplate: Next.js Pages Router, shadcn-style UI components, FastAPI, PostgreSQL, bcrypt password hashes, and JWT authentication.

## Run locally

```bash
docker compose up --build
```

- Web app: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

Local demo accounts:

- Reader: `demo@example.com` / `password`
- Admin: `admin@example.com` / `admin123`

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

Configure a strong `JWT_SECRET` and unique `SEED_ADMIN_PASSWORD` outside development. The Compose defaults are for local coursework only. In a deployed environment, terminate TLS at a trusted HTTPS proxy/load balancer and do not expose the development credentials or database port publicly.
